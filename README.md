# operit-comfyui-mcp 🔧🎸

MCP（Model Context Protocol）服务器，在 Operit 中无缝操控你的电脑端 ComfyUI —— 无需切屏，手机上一句话就能让 ComfyUI 生图！

## 原项目

- GitHub: [ComfyUI](https://github.com/comfyui/comfyui)
- 用途: 通过 MCP 协议，让 Operit AI 助手直接调用你电脑上运行的 ComfyUI

## 功能

- 🖼️ 加载现有工作流（ComfyUI workflow）
- 🎨 实时调整工作流参数
- ⚡ 智能纠错！不怕缺节点，自动修复
- 🔐 隐私保障（本地运行，懂的都懂）
- 🖱️ 随时查看队列状态
- 🎲 加载工作流直接生成，无需手动导出

一句话：**你只管在手机上动嘴，ComfyUI 在电脑上干活。**

## 安装

### 方法一：AI 自动安装 🤖
把仓库链接扔给你的 AI 助手，让它帮你搞定~

### 方法二：手动安装 ✋
```bash
git clone https://github.com/MengXinSu/operit-comfyui-mcp
cd operit-comfyui-mcp
pip install -e .
```
然后将 MCP 配置加入 Operit 即可。

### ⚠️ 别忘了

**ComfyUI 在电脑上保持运行**，Operit 在手机上连接使用。首次生图较慢（需编译 Shader），后续飞快~

## ⚖️ 许可证

CC BY-NC 4.0 — <A href="./LICENSE">详见许可证文件</A>

- 📝 **项目地址**: https://github.com/MengXinSu/operit-comfyui-mcp
- 🎮 **自用随意**，禁止商用

---

*Powered by ComfyUI 🎲 Made with love by MengXinSu*