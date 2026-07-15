# 嵌入式构建工作区顶部对齐设计

## 背景

共享构建工作区在独立 CI/CD 页面中使用 `top: 80px` 吸顶，以避开 68px 全局导航并保留间距。
当同一工作区嵌入 Application 的 Element Plus Tab 内容区时，Tab 的 overflow 容器成为 sticky
参照，80px 偏移会立即作用在左侧历史栏，导致它比右侧详情低一截并产生顶部留白。

## 设计

- 保持共享工作区默认 `top: 80px`，独立 CI/CD 页面行为不变。
- 在 `ApplicationDetail` 的 Pipeline Tab 宿主范围内，把共享工作区历史栏的 sticky `top`
  覆盖为 `0`，让左右两列顶部对齐。
- 保留历史栏视口高度、内部滚动、列宽以及 760px 移动端复位规则。
- 不复制共享组件内容，也不改变构建选择、日志、轮询或 API 行为。

## 验证

- 生产 CSS 中同时存在共享默认 `top: 80px` 和 Application 宿主级 `top: 0` 覆盖。
- 前端测试、类型检查、生产构建和 `./scripts/verify.sh` 通过。
