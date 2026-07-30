# operit-comfyui-mcp

Operit 本地 MCP 插件，让 AI 助手调用电脑上运行的 ComfyUI 生成图像。

## 工作原理

ComfyUI 跑在电脑上，这个插件让手机上的 Operit 通过 MCP 协议跟它通信。
手机上发指令，电脑出图。

## 前置条件

- 电脑上已安装并运行 ComfyUI
- 手机和电脑在同一局域网
- Operit 中已配置此 MCP 插件

## 功能

### 连接与状态

- **comfy_connect(host)** — 连接 ComfyUI 服务器，host 填 `IP:8188`
- **comfy_system_stats()** — 查看系统信息（Python版本、CUDA/GPU、显存）
- **comfy_free_vram()** — 释放显存，卸载模型

### 工作流管理

- **comfy_list_workflows()** — 列出所有可用工作流
- **comfy_load_workflow(name, json_string, file_path)** — 加载工作流
- **comfy_get_workflow_params(name)** — 查看工作流可调参数
- **comfy_get_recent_workflows(limit)** — 查看最近执行过的工作流
- **comfy_load_from_history(prompt_id)** — 从历史记录重新加载工作流

### 生成

- **comfy_generate(workflow_name, params, wait)** — 修改参数并执行生成
- **comfy_quick_gen(file_path, params)** — 从文件快速加载并生成
- **comfy_get_result(prompt_id)** — 获取某次生成的结果
- **comfy_upload_image(file_path)** — 上传图片到 ComfyUI 输入目录

### 诊断与修复

- **comfy_list_nodes()** — 列出 ComfyUI 已安装的所有节点类型
- **comfy_list_models(folder)** — 列出指定目录下的模型
- **comfy_check_compatibility(name)** — 检查工作流是否有缺失节点
- **comfy_fix_workflow(name)** — 自动修复缺失节点

### 队列控制

- **comfy_queue_status()** — 查看当前执行队列
- **comfy_interrupt()** — 中断当前正在执行的工作流

## 使用步骤

1. 电脑上启动 ComfyUI（加 --listen 参数允许远程连接）
2. 在 Operit 中调 comfy_connect 连接你的 ComfyUI
3. 调 comfy_list_workflows 看有哪些工作流
4. 调 comfy_load_workflow 加载一个
5. 调 comfy_generate 改提示词，开始生图

> 首次生图较慢（ComfyUI 需编译 Shader），之后就快了。

## 注意事项

- 工作流路径基于 ComfyUI 的 user/default/workflows 目录
- 图片保存到 ComfyUI 的 output 目录
- 连不上先检查网络
- 理论上也可以生成视频（需使用 AnimateDiff 等视频工作流），但 Operit 暂无视频播放功能，需要 AI 将视频文件放到指定位置供你查看

## 许可证

本项目采用 CC BY-NC 4.0（署名-非商业使用）许可证。
可以自由分享、修改，但需署名原作者且不得用于商业用途。
详见 LICENSE 文件。