# CI Test Project

这是一个简单的持续集成测试项目，用于演示GitHub Actions的基本功能。

## 功能特点

- 自动化构建和测试
- 环境配置示例
- 工作流程自动化

## 使用方法

1. Fork 此仓库
2. 在仓库设置中配置必要的 Secrets
3. 手动触发工作流程

## 配置说明

在仓库的 Settings > Secrets and variables > Actions 中配置以下变量：

- `TUNNEL_TOKEN`: 用于环境配置
- `RDP_PASSWORD`: 用于环境访问

## 注意事项

- 请确保配置的密码符合复杂度要求
- 定期更新配置信息
- 及时关闭不需要的工作流程