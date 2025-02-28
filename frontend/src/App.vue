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
        <p>© 2024 GitHub开发者能力评估 | 基于GitHub API构建</p>
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
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', Arial, sans-serif;
  background-color: #f5f7fa;
  color: #303133;
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
  background: linear-gradient(135deg, #f5f7fa 0%, #e4e7eb 100%);
  background-attachment: fixed;
}

.app-header {
  background-color: #24292e;
  color: white;
  padding: 15px 30px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.logo {
  display: flex;
  align-items: center;
}

.logo img {
  height: 40px;
  margin-right: 15px;
}

.logo h1 {
  font-size: 20px;
  font-weight: 600;
}

.header-links {
  display: flex;
  gap: 20px;
}

.header-links a {
  color: #ffffff;
  text-decoration: none;
  font-size: 16px;
  transition: color 0.3s;
}

.header-links a:hover {
  color: #58a6ff;
}

.app-footer {
  margin-top: auto;
  text-align: center;
  padding: 20px;
  background-color: #24292e;
  color: #8b949e;
}

/* Element Plus 全局样式覆盖 */
:root {
  --el-color-primary: #0366d6;
}

.el-button--primary {
  background-color: #0366d6;
  border-color: #0366d6;
}

.el-button--primary:hover,
.el-button--primary:focus {
  background-color: #0679fc;
  border-color: #0679fc;
}

.el-tabs__item.is-active {
  color: #0366d6;
}

.el-tabs__active-bar {
  background-color: #0366d6;
}

.el-pagination.is-background .el-pager li:not(.disabled).active {
  background-color: #0366d6;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .app-header {
    flex-direction: column;
    padding: 15px;
  }
  
  .logo {
    margin-bottom: 10px;
  }
  
  .header-links {
    width: 100%;
    justify-content: space-around;
  }
}
</style>
