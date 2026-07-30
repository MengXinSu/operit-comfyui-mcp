# operit-comfyui-mcp

一个 MCP 服务器，让 Operit AI 助手可以调用电脑上运行的 ComfyUI 生成图像。

## 工作原理

ComfyUI 运行在你的电脑上，这个插件让 Operit（手机上）能通过 MCP 协议跟它通信。
在手机上下指令，电脑上的 ComfyUI 干活出图。

## 前置条件

- 电脑上已经装好并运行 ComfyUI（https://github.com/comfyui/comfyui）
- 手机和电脑在同一局域网，或者 ComfyUI 暴露了可访问的地址
- Operit 中已配置好 MCP 插件

## 功能列表

### 1. 连接管理

**comfy_connect(host)**
连接到运行 ComfyUI 的服务器。
- 参数：host — 地址，例如 192.168.1.100:8188
- 默认连本机 127.0.0.1:8188

**comfy_status()**
查看当前连接状态——是否连上了、队列有多少任务。

### 2. 工作流管理

**comfy_list_workflows(dir_path)**
列出 ComfyUI 工作流目录下的所有文件。
- 参数：dir_path — 目录路径（基于 ComfyUI 用户目录的相对路径）

**comfy_load_workflow(workflow_path)**
加载一个工作流，返回可编辑的参数列表。
- 参数：workflow_path — 工作流文件路径

**comfy_get_workflow(workflow_path)**
查看工作流的完整内容。

### 3. 参数调整 & 生成

**comfy_set_params(workflow_path, params)**
修改工作流里的参数（提示词、尺寸、种子等），然后执行生成。
- 参数：
  - workflow_path — 工作流文件路径
  - params — 要修改的参数列表
- 返回：生成的图片列表

**comfy_fix_workflow(workflow_path)**
如果工作流里缺节点或配置有问题，自动尝试修复。

**comfy_get_result(prompt_id)**
获取某次生成的图片结果。
- 参数：prompt_id — 之前 comfy_set_params 返回的任务 ID

### 4. 队列 & 清理

**comfy_queue()**
查看 ComfyUI 当前执行队列。

**comfy_clear_queue()**
清空队列中所有等待任务。

## 使用方法

1. 电脑上启动 ComfyUI（确保 --listen 或设置允许远程访问）
2. 在 Operit 中已配置此插件的前提下，调用 comfy_connect 连上你的 ComfyUI 地址
3. 用 comfy_list_workflows 看看有哪些工作流可用
4. 用 comfy_load_workflow 加载一个工作流
5. 用 comfy_set_params 改提示词，开始生图

首次生图会慢一些（ComfyUI 需要编译 Shader），后面就快了。

## 注意事项

- 工作流文件路径基于 ComfyUI 自己的 user/default/workflows 目录
- 图片会保存到 ComfyUI 的 output 目录
- 连接不上时先检查电脑和手机是否在同一网络

## 仓库说明

这是一个对 operit-comfyui-mcp 原项目（https://github.com/xororz/operit-comfyui-mcp）的修改版本，清理了示例配置中的示例 IP 地址，除此之外功能与原版一致。

## 许可证

CC BY-NC 4.0 — 详见 LICENSE

---

项目地址：https://github.com/MengXinSu/operit-comfyui-mcp