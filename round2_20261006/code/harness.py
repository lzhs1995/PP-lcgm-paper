"""调用本机工作台证据工具，不替代原生 MCP 调用。"""
import runpy
import sys
sys.path.insert(0, r'C:\Users\LZHS\.agents\skills\clauder-rstudio-workbench')
sys.argv[0] = 'clauder_workbench'
runpy.run_module('clauder_workbench', run_name='__main__')
