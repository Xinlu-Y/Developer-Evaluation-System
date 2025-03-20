/**
 * 增强版Markdown到HTML转换函数
 * 支持更多技术评估格式：标题、列表、粗体、斜体、代码等
 * @param {string} markdown
 * @returns {string} HTML文本
 */
export function markdownToHtml(markdown) {
  if (!markdown) return '';
  
  let html = markdown;
  
  // 处理技术评估中的专业部分
  html = html.replace(/^###?\s+技术栈全面评估[：:](.*?)(?=^###?\s+|$)/gms, '<div class="skill-section tech-stack"><h3>技术栈全面评估</h3>$1</div>');
  html = html.replace(/^###?\s+专业领域和专长[：:](.*?)(?=^###?\s+|$)/gms, '<div class="skill-section domains"><h3>专业领域和专长</h3>$1</div>');
  html = html.replace(/^###?\s+项目经验分析[：:](.*?)(?=^###?\s+|$)/gms, '<div class="skill-section projects"><h3>项目经验分析</h3>$1</div>');
  html = html.replace(/^###?\s+技术成长与潜力[：:](.*?)(?=^###?\s+|$)/gms, '<div class="skill-section growth"><h3>技术成长与潜力</h3>$1</div>');
  html = html.replace(/^###?\s+技术协作与贡献[：:](.*?)(?=^###?\s+|$)/gms, '<div class="skill-section collaboration"><h3>技术协作与贡献</h3>$1</div>');
  
  // 处理标题 (h1, h2, h3)
  html = html.replace(/^### (.*?)$/gm, '<h3>$1</h3>');
  html = html.replace(/^## (.*?)$/gm, '<h2>$1</h2>');
  html = html.replace(/^# (.*?)$/gm, '<h1>$1</h1>');
  
  // 处理编程语言和技术栈关键词突出显示
  const technologies = [
    'JavaScript', 'TypeScript', 'Python', 'Java', 'C\\+\\+', 'C#', 'Go', 'Rust', 'PHP', 'Ruby', 'Swift',
    'React', 'Vue', 'Angular', 'Node.js', 'Express', 'Django', 'Flask', 'Spring', 'Laravel', 'TensorFlow',
    'PyTorch', 'Docker', 'Kubernetes', 'AWS', 'Azure', 'GCP', 'SQL', 'NoSQL', 'MongoDB', 'Redis',
    'PostgreSQL', 'MySQL', 'GraphQL', 'REST', 'CI/CD', 'Git', 'DevOps', 'Microservices', 'Machine Learning',
    'Deep Learning', 'AI', 'Data Science', 'Big Data', 'Blockchain', 'IoT', 'Mobile', 'Web', 'Frontend',
    'Backend', 'Fullstack'
  ];
  
  // 使用正则表达式匹配整个单词，确保只匹配完整的技术名称
  technologies.forEach(tech => {
    const regex = new RegExp(`\\b${tech}\\b`, 'g');
    html = html.replace(regex, `<span class="tech-highlight">${tech}</span>`);
  });
  
  // 处理粗体
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/__(.*?)__/g, '<strong>$1</strong>');
  
  // 处理斜体
  html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
  html = html.replace(/_(.*?)_/g, '<em>$1</em>');
  
  // 处理列表
  html = html.replace(/^\* (.*?)$/gm, '<li>$1</li>');
  html = html.replace(/^- (.*?)$/gm, '<li>$1</li>');
  
  // 将连续的li元素包裹在ul中
  html = html.replace(/(<li>.*?<\/li>)+/g, '<ul>$&</ul>');
  
  // 处理代码段
  html = html.replace(/`(.*?)`/g, '<code>$1</code>');
  
  // 处理评分显示，如：掌握程度：★★★★☆
  html = html.replace(/(掌握程度|熟练度|专精度|评分)[:：]\s*(★+☆*)/g, 
    '<div class="skill-rating"><span class="rating-label">$1:</span><span class="rating-stars">$2</span></div>');
  
  // 处理段落（将多个换行符替换为段落标签）
  html = html.replace(/\n\n+/g, '</p><p>');
  html = '<p>' + html + '</p>';
  html = html.replace(/<p><\/p>/g, '');
  
  // 处理换行（单个换行）
  html = html.replace(/\n/g, '<br>');
  
  // 添加技术能力总结的整体容器
  html = `<div class="dev-skill-summary">${html}</div>`;
  
  return html;
} 