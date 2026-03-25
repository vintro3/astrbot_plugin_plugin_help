from astrbot.api.all import *
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register

# 尝试导入系统底层指令注册表
try:
    from astrbot.core.star.star_handler import star_handlers_registry
except ImportError:
    star_handlers_registry = []

@register("command_menu", "Developer", "自动分类读取并展示已加载插件的指令列表", "1.0")
class CommandMenu(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    def _get_plugins_with_commands(self):
        """扫描所有插件并提取指令，进行名称清洗和去重"""
        plugins_dict = {}
        
        for handler in star_handlers_registry:
            commands = []
            for f in getattr(handler, "event_filters", []):
                cls_name = type(f).__name__
                if cls_name == "CommandFilter":
                    cmd = getattr(f, "command_name", None)
                    if cmd: commands.append(str(cmd).lstrip('/')) 
                elif cls_name == "CommandGroupFilter":
                    cmd = getattr(f, "group_name", None)
                    if cmd: commands.append(str(cmd).lstrip('/'))
            
            if not commands: continue
            
            # 识别插件来源
            plugin_name = "未知插件"
            func = getattr(handler, "call", getattr(handler, "func", None))
            if hasattr(func, "__self__"):
                plugin_inst = func.__self__
                plugin_name = getattr(plugin_inst, "plugin_name", getattr(plugin_inst, "name", plugin_inst.__class__.__name__))
            else:
                module_path = getattr(handler, "handler_module_path", "")
                if "astrbot_plugin" in module_path:
                    for part in module_path.split("."):
                        if part.startswith("astrbot_plugin"):
                            plugin_name = part
                            break

            # 过滤系统内置指令及自身
            if plugin_name in ["未知插件", "star_handler", "builtin", "core", "command_menu", "CommandMenu"]: 
                continue
            
            clean_name = plugin_name.replace("astrbot_plugin_", "", 1) if plugin_name.startswith("astrbot_plugin_") else plugin_name

            if clean_name not in plugins_dict:
                plugins_dict[clean_name] = []
            plugins_dict[clean_name].extend(commands)
            
        for k in plugins_dict:
            plugins_dict[k] = sorted(list(set(plugins_dict[k])))
        return plugins_dict

    @filter.command("菜单")
    async def show_menu(self, event: AstrMessageEvent, plugin_name: str = ""):
        '''获取插件指令列表。用法: /菜单 [插件名]'''
        
        # 在函数最开始强行拦截大模型，确保所有分支都不会漏过去
        event.stop_event()
        
        plugins_dict = self._get_plugins_with_commands()
        if not plugins_dict:
            yield event.plain_result("未检测到已加载的外部插件指令。")
            return

        if plugin_name:
            matches = [k for k in plugins_dict.keys() if plugin_name.lower() in k.lower()]
            
            if len(matches) > 1:
                msg = f"检测到多个匹配的插件 ({len(matches)}): \n"
                for m in matches: msg += f"- {m}\n"
                msg += "\n请输入更具体的插件名称进行查询。"
                yield event.plain_result(msg)
            elif len(matches) == 1:
                target = matches[0]
                msg = f"【{target}】插件指令列表: \n\n"
                for cmd in plugins_dict[target]:
                    msg += f"/{cmd}\n"
                yield event.plain_result(msg)
            else:
                yield event.plain_result(f"未找到名称包含 '{plugin_name}' 的插件。")
            return

        msg = "已加载插件指令目录: \n\n"
        for name, cmds in sorted(plugins_dict.items()):
            msg += f"• {name} ({len(cmds)} 条指令)\n"
        msg += "\n提示: 输入 [/菜单 插件名] 查看具体指令。"
        yield event.plain_result(msg)