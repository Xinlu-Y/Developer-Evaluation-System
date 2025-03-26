<template>
  <div id="app">
    <div class="app-background">
      <div class="app-header">
        <div class="logo">
          <img src="https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png" alt="GitHub Logo" />
          <h1>GitHub开发者能力评估</h1>
        </div>
        <div class="header-links">
          <a href="https://github.com" target="_blank">GitHub</a>
          <a href="https://docs.github.com/cn" target="_blank">文档</a>
          <a href="https://github.com/trending" target="_blank">趋势</a>
        </div>
      </div>
      <router-view></router-view>
      <div class="app-footer">
        <p>© 2025 GitHub开发者能力评估 | 基于GitHub API构建</p>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'App'
}
</script>

<style>
/* 全局样式 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  background-color: #ffffff;
  color: #37352f;
  line-height: 1.5;
}

#app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-background {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background-color: #ffffff;
}

.app-header {
  background-color: #ffffff;
  border-bottom: 1px solid #e5e5e5;
  padding: 12px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  position: sticky;
  top: 0;
  z-index: 100;
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo img {
  height: 32px;
}

.logo h1 {
  font-size: 18px;
  font-weight: 600;
  color: #37352f;
}

.header-links {
  display: flex;
  gap: 24px;
}

.header-links a {
  color: #787774;
  text-decoration: none;
  font-size: 14px;
  transition: color 0.2s;
  padding: 4px 8px;
  border-radius: 4px;
}

.header-links a:hover {
  color: #37352f;
  background-color: #f5f5f5;
}

.app-footer {
  margin-top: auto;
  text-align: center;
  padding: 24px;
  border-top: 1px solid #e5e5e5;
  color: #787774;
  font-size: 14px;
}

/* Element Plus 全局样式覆盖 */
:root {
  --el-color-primary: #2eaadc;
  --el-color-primary-light-3: #4bc8e8;
  --el-color-primary-light-5: #7dd5ed;
  --el-color-primary-light-7: #aee2f2;
  --el-color-primary-light-8: #c5e9f6;
  --el-color-primary-light-9: #e8f6fa;
  --el-color-primary-dark-2: #2589b0;
}

.el-button--primary {
  background-color: #2eaadc;
  border-color: #2eaadc;
  border-radius: 4px;
  font-weight: 500;
  transition: all 0.2s;
}

.el-button--primary:hover,
.el-button--primary:focus {
  background-color: #2589b0;
  border-color: #2589b0;
}

.el-tabs__item {
  font-size: 14px;
  color: #787774;
  transition: all 0.2s;
}

.el-tabs__item.is-active {
  color: #2eaadc;
  font-weight: 500;
}

.el-tabs__active-bar {
  background-color: #2eaadc;
  height: 2px;
}

.el-pagination.is-background .el-pager li:not(.disabled).active {
  background-color: #2eaadc;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .app-header {
    padding: 12px 16px;
  }
  
  .logo {
    margin-bottom: 0;
  }
  
  .header-links {
    gap: 16px;
  }
}
</style>
