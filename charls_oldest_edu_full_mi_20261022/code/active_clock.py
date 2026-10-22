"""Windows清醒时间预算；保留真实墙钟，不把睡眠/休眠计作估计超时。"""
import ctypes,time,datetime,subprocess,xml.etree.ElementTree as ET
_k=ctypes.WinDLL('kernel32',use_last_error=True)
_q=_k.QueryUnbiasedInterruptTime
_q.argtypes=[ctypes.POINTER(ctypes.c_ulonglong)];_q.restype=ctypes.c_int
def active_now():
    value=ctypes.c_ulonglong()
    if not _q(ctypes.byref(value)):raise ctypes.WinError(ctypes.get_last_error())
    return value.value/10_000_000
class BudgetClock:
    def __init__(self,active=active_now,wall=time.monotonic):
        self.active=active;self.wall=wall;self.a0=active();self.w0=wall();self.last_a=self.a0;self.last_w=self.w0;self.last_utc=datetime.datetime.now(datetime.timezone.utc);self.extra=0.;self.power_events=[]
    def sample(self):
        now_a=self.active();now_w=self.wall();now_utc=datetime.datetime.now(datetime.timezone.utc);da=now_a-self.last_a;dw=now_w-self.last_w
        # S0低功耗期间有短暂系统活动；大采样空档额外核对明确的睡眠事件，避免双重扣除。
        if dw>30 and self.active is active_now:
            try:
                events=power_sleep_events(self.last_utc,now_utc);sleep=sum(x['overlap_seconds'] for x in events)
                assert sleep<=dw+2
                additional=max(0,sleep-max(0,dw-da));self.extra+=additional
                if events:self.power_events.append(dict(events=events,additional_exclusion=additional))
            except Exception as exc:self.power_events.append(dict(query_error=repr(exc),wall_gap=dw))
        self.last_a=now_a;self.last_w=now_w;self.last_utc=now_utc
        a=max(0,now_a-self.a0-self.extra);w=now_w-self.w0
        return dict(active_seconds=a,raw_unbiased_seconds=now_a-self.a0,wall_seconds=w,excluded_suspend_seconds=max(0,w-a),power_events=self.power_events)
    def expired(self,limit):return self.sample()['active_seconds']>=limit

def parse_power_sleep(xml,start,end):
    ns={'e':'http://schemas.microsoft.com/win/2004/08/events/event'};root=ET.fromstring('<Events>'+xml+'</Events>');rows=[]
    for event in root:
        if event.findtext('e:System/e:EventID',namespaces=ns)!='507':continue
        data={x.attrib.get('Name'):x.text for x in event.findall('e:EventData/e:Data',ns)}
        if data.get('SleepEntered')!='true':continue
        stamp=event.find('e:System/e:TimeCreated',ns).attrib['SystemTime'];exit_time=datetime.datetime.fromisoformat(stamp.replace('Z','+00:00'))
        duration=float(data.get('SleepDurationInUs','0'))/1e6
        if not 0<duration<86400:continue
        entry=exit_time-datetime.timedelta(seconds=duration);overlap=max(0,(min(end,exit_time)-max(start,entry)).total_seconds())
        if overlap:rows.append(dict(exit_utc=stamp,sleep_seconds=duration,overlap_seconds=overlap))
    return rows

def power_sleep_events(start,end):
    stamp=start.isoformat(timespec='milliseconds').replace('+00:00','Z')
    query=f"/q:*[System[Provider[@Name='Microsoft-Windows-Kernel-Power'] and EventID=507 and TimeCreated[@SystemTime >= '{stamp}']]]"
    p=subprocess.run(['C:/Windows/System32/wevtutil.exe','qe','System',query,'/f:xml','/c:24','/rd:true'],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=8,creationflags=0x08000000)
    if p.returncode:raise RuntimeError(p.stderr[:300])
    return parse_power_sleep(p.stdout,start,end)
