# operit-comfyui-mcp

一个 MCP 服务器，让 Operit AI 助手调用电脑上运行的 ComfyUI 生成图像。

## 工作原理

ComfyUI 跑在电脑上，这个插件让手机上的 Operit 通过 MCP 协议跟它通信。
手机上发指令，电脑出图。

## 前置条件

- 电脑上已安装并运行 ComfyUI
- 手机和电脑在同一局域网
- Operit 中已配置此 MCP 插件

## 功能

### 连接

- **comfy_connect(host)** — 连接 ComfyUI 服务器，host 填 IP 地址
- **comfy_status()** — 查看当前连接状态和队列

### 工作流

- **comfy_list_workflows(dir_path)** — 列出工作流目录下的文件
- **comfy_load_workflow(workflow_path)** — 加载工作流，返回可调参数
- **comfy_get_workflow(workflow_path)** — 查看工作流完整内容

### 生成

- **comfy_set_params(workflow_path, params)** — 改参数（提示词、尺寸、种子等）并执行生成，返回图片
- **comfy_fix_workflow(workflow_path)** — 工作流出错时自动修复
- **comfy_get_result(prompt_id)** — 获取某次生成的结果

### 队列

- **comfy_queue()** — 查看当前队列
- **comfy_clear_queue()** — 清空队列

## 使用步骤

1. 电脑上启动 ComfyUI（加 --listen 参数允许远程连接）
2. 在 Operit 中调 comfy_connect 连接你的 ComfyUI
3. 用 comfy_list_workflows 看有哪些工作流
4. 用 comfy_load_workflow 加载一个
5. 用 comfy_set_params 改提示词，开始生图

> 首次生图较慢（ComfyUI 需编译 Shader），之后就快了。

## 注意事项

- 工作流路径基于 ComfyUI 的 user/default/workflows 目录
- 图片保存到 ComfyUI 的 output 目录
- 连不上先检查网络

## 许可证

本项目采用 CC BY-NC 4.0（署名-非商业使用）许可证。
可以自由分享、修改，但需署名原作者且不得用于商业用途。
详见仓库中的 LICENSE 文件。