/**
 * TG AI Chat Bot - Official Website Scripts
 * Handles i18n, interactions, animations, and navigation
 */
(function () {
  'use strict';

  // ================================================================
  // Internationalization Data
  // ================================================================
  // Store original English text on first load so we can restore it
  const _originalText = new Map();

  function _captureOriginalText() {
    document.querySelectorAll('[data-i18n]').forEach(el => {
      if (!_originalText.has(el.dataset.i18n)) {
        _originalText.set(el.dataset.i18n, el.textContent);
      }
    });
    document.querySelectorAll('[data-i18n-nav]').forEach(el => {
      if (!_originalText.has(el.dataset.i18nNav)) {
        _originalText.set(el.dataset.i18nNav, el.textContent);
      }
    });
  }

  const i18n = {
    zh: {
      // Nav
      features: "核心功能",
      architecture: "系统架构",
      plugins: "插件系统",
      quickstart: "快速开始",
      faq: "常见问题",

      // Hero
      hero_badge: "开源项目 / MIT 许可证",
      hero_title_1: "轻量级 Telegram",
      hero_title_2: "多 Bot AI",
      hero_title_3: "聊天系统",
      hero_desc: "一个生产级的 Telegram 智能聊天机器人平台，支持多 LLM 后端、Bot 动态管理、插件扩展和全功能 Web 管理面板。一键部署，无限扩展。",
      hero_btn_start: "快速开始",
      hero_stat_models: "LLM 供应商",
      hero_stat_plugins: "内置插件",
      hero_stat_layers: "架构分层",
      hero_stat_apis: "REST API",

      // Features
      features_tag: "核心能力",
      features_title: "构建智能 Telegram Bot 所需的一切",
      features_desc: "从多模型推理到插件编排，从会话记忆到 Web 管理 -- 全部内置。",
      feat_multi_title: "多 Bot 热管理",
      feat_multi_desc: "通过 Web 面板随时添加、删除、启动或停止 Bot 实例。无需重启服务。每个 Bot 具有独立的性格、模型选择和群聊策略。",
      feat_model_title: "12+ LLM 后端与自动故障转移",
      feat_model_desc: "支持 OpenAI、DeepSeek、Claude、Gemini、通义千问、Moonshot、智谱、阶跃星辰、MiniMax、百度文心、字节豆包和 Ollama。主模型失败时自动切换备份模型 -- 零停机。",
      feat_plugin_title: "Function Calling 插件系统",
      feat_plugin_desc: "9 个内置插件：网页搜索、URL 摘要、天气查询、计算器、翻译、图片生成、CLI 沙箱、图片理解和 Memos 集成。通过简洁的 Python 接口扩展。",
      feat_security_title: "安全与沙箱",
      feat_security_desc: "JWT 认证 + 恢复码重置密码、黑名单、频率限制、白名单模式、CLI 沙箱（资源限制+危险命令拦截）、日志自动脱敏。",
      feat_memory_title: "隔离会话记忆",
      feat_memory_desc: "bot_id + chat_id 隔离确保每个对话独立。自动摘要功能在超过 30 条消息时压缩对话，保留最近 8 条以保持上下文连贯。",
      feat_web_title: "全功能 Web 管理面板",
      feat_web_desc: "React + Vite 构建的仪表盘，支持实时统计、Bot 管理、模型配置、插件开关、黑名单控制、会话查看、诊断和每个 Bot 的性格设置。",

      // Architecture
      arch_tag: "系统设计",
      arch_title: "七层清晰架构",
      arch_desc: "从底层到顶层关注点分离。每个层具有单一职责，使系统易于理解、维护和扩展。",
      arch_l1_title: "Telegram Bot 层",
      arch_l1_desc: "消息路由、20+ 命令、多模态对话、结构化上下文注入",
      arch_l2_title: "核心逻辑层",
      arch_l2_desc: "LLM 抽象（OpenAI / Anthropic / Ollama）、会话记忆、运行时配置、Bot 实例管理",
      arch_l3_title: "插件/连接器系统",
      arch_l3_desc: "9 个内置插件、统一接口、LLM 自动工具调用、手动命令触发",
      arch_l4_title: "存储层",
      arch_l4_desc: "SQLite 含 7 张关系表、异步 I/O、自动迁移、对话摘要",
      arch_l5_title: "工具层",
      arch_l5_desc: "结构化日志（自动脱敏）、Markdown 转 Telegram HTML 转换器",
      arch_l6_title: "Web API 层",
      arch_l6_desc: "FastAPI 含 30+ REST 端点、JWT 认证 + bcrypt、前端静态文件服务",
      arch_l7_title: "React 前端",
      arch_l7_desc: "仪表盘、Bot/模型/插件管理、黑名单、会话、诊断、逐 Bot 性格编辑器",

      // Plugins
      plugins_tag: "可扩展插件",
      plugins_title: "9 个内置连接器，无限可能性",
      plugins_desc: "LLM 可通过 Function Calling 自动决策调用工具，用户也可通过斜杠命令手动触发插件。",
      plugin_web_search: "网页搜索",
      plugin_web_search_desc: "DuckDuckGo + DDG Instant Answer API 双 fallback",
      plugin_url: "URL 摘要",
      plugin_url_desc: "httpx 抓取 + BeautifulSoup 解析提取文章内容",
      plugin_weather: "天气查询",
      plugin_weather_desc: "通过 wttr.in 免费 API 查询全球天气",
      plugin_calc: "计算器",
      plugin_calc_desc: "基于 AST 的安全表达式求值，支持数学函数",
      plugin_translate: "翻译",
      plugin_translate_desc: "通过 LLM 实现多语言翻译",
      plugin_image_gen: "图片生成",
      plugin_image_gen_desc: "通过 OpenAI API 调用 DALL-E 生成图片",
      plugin_cli: "CLI 沙箱",
      plugin_cli_desc: "容器 Shell 命令执行，含资源限制和安全黑名单",
      plugin_image_understand: "图片理解",
      plugin_image_understand_desc: "多模态模型自动路由，base64 图片直传",
      plugin_memos: "Memos 备忘录",
      plugin_memos_desc: "个人知识库集成 -- 列表/搜索/创建/更新/删除",

      // Tech Stack
      tech_tag: "技术栈",
      tech_title: "现代化、生产就绪的技术栈",
      tech_desc: "精心挑选经过实战检验的技术，在性能、可维护性和开发体验之间取得平衡。",
      tech_cat_bot: "Bot 框架",
      tech_cat_llm: "LLM 与 AI",
      tech_cat_backend: "后端",
      tech_cat_frontend: "前端",
      tech_cat_auth: "认证与安全",
      tech_cat_tools: "工具与库",
      tech_cat_deploy: "部署",

      // Quick Start
      qs_tag: "开始使用",
      qs_title: "秒级部署",
      qs_desc: "选择适合您工作流程的部署方式。",
      qs_docker_title: "Docker（推荐）",
      qs_prod_title: "生产环境部署",
      qs_dev_title: "本地开发",
      qs_after: "部署完成后，访问 <code>http://localhost:8000</code> 进入 Web 管理面板。首次登录设置管理密码，然后添加您的 Telegram Bot Token 即可开始使用。",

      // Screenshots
      ss_tag: "管理面板",
      ss_title: "直观的 Web 管理界面",
      ss_desc: "通过简洁的 React 仪表盘全面掌控您的 Bot、模型、插件和对话。",
      ss_dashboard: "仪表盘",
      ss_dashboard_desc: "消息数量、Token 消耗、活跃用户、模型概览与连接器状态",
      ss_bots: "Bot 管理",
      ss_bots_desc: "添加/编辑/删除 Bot、Token 验证、5 种预设角色的性格编辑器",
      ss_models: "模型配置",
      ss_models_desc: "12+ 供应商预设、模型列表查询、连接测试、主模型切换",
      ss_plugins: "插件开关",
      ss_plugins_desc: "一键启用/禁用 9 个插件中的任意一个",
      ss_blacklist: "黑名单控制",
      ss_blacklist_desc: "添加/移除用户以阻止不必要的交互",
      ss_diagnostics: "系统诊断",
      ss_diagnostics_desc: "Bot 连接状态、轮询检查及故障排查指南",

      // FAQ
      faq_tag: "常见问题",
      faq_title: "常见问题解答",
      faq_q1: "支持哪些 LLM 供应商？",
      faq_a1: "系统支持 12+ 供应商：OpenAI、DeepSeek、Anthropic Claude、Google Gemini、阿里通义千问、Moonshot、智谱 AI (GLM)、阶跃星辰、MiniMax、百度文心 (ERNIE)、字节豆包，以及用于本地模型的 Ollama。每个 Bot 可以配置一个主模型和一个备份模型，支持自动故障转移。",
      faq_q2: "一次部署可以运行多个 Telegram Bot 吗？",
      faq_a2: "可以。系统支持无限数量的 Bot 实例同时运行。每个 Bot 拥有独立的性格、模型配置、群聊设置和插件偏好。您可以随时通过 Web 面板添加、删除、启动或停止 Bot，无需重启服务。",
      faq_q3: "插件/Function Calling 系统是如何工作的？",
      faq_a3: "每个插件暴露一个 OpenAI Function Calling 格式的工具定义。当用户发送消息时，工具定义随对话一起发送给 LLM。LLM 自行决定是否调用工具。系统执行工具并将结果返回给 LLM 以生成最终回复。用户也可以手动通过 /search、/weather、/calc、/translate、/draw 等命令触发插件。",
      faq_q4: "对话记忆是如何处理的？",
      faq_a4: "对话历史存储在 SQLite 中，按 bot_id + chat_id 隔离。当对话超过 30 条消息时，系统自动触发基于 LLM 的摘要，压缩旧消息，同时保留最近 8 条消息和先前上下文的摘要。这在保持上下文连贯性和 Token 效率之间取得了平衡。",
      faq_q5: "系统有哪些安全措施？",
      faq_a5: "系统实现了多层安全措施：基于 JWT 的认证（24小时 Token 过期）、bcrypt 密码哈希、12 位恢复码用于密码重置、用户黑名单、每用户频率限制、白名单模式选项、CLI 沙箱（256MB 内存限制和危险命令黑名单），以及 API Key 和 Token 的日志自动脱敏。",
      faq_q6: "如何扩展系统添加新插件？",
      faq_a6: "创建新插件非常简单：继承 PluginBase 基类，实现 execute() 方法和 get_tool_definition() 方法，然后在插件注册中心注册。其余由系统自动处理 -- 您的插件将自动出现在 Function Calling 工具列表中，并可通过 Web 面板启用/禁用。",

      // Footer
      footer_desc: "一个轻量级、生产就绪的 Telegram 多 Bot AI 聊天系统。基于 MIT 许可证开源。",
      footer_resources: "资源",
      footer_readme: "README",
      footer_license: "许可证",
      footer_deploy: "部署",
      footer_docker: "Docker",
      footer_prod: "生产环境",
      footer_dev: "本地开发",
      footer_built: "用",
      footer_by: "构建 by",
    },
  };

  let currentLang = 'zh';

  // ================================================================
  // Language Switching
  // ================================================================
  function setLanguage(lang) {
    currentLang = lang;

    // Update lang buttons
    document.querySelectorAll('.lang-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.lang === lang);
    });

    // Update HTML lang attribute
    document.documentElement.lang = lang === 'zh' ? 'zh-CN' : 'en';

    const translations = i18n[lang];

    // Update all data-i18n elements
    document.querySelectorAll('[data-i18n]').forEach(el => {
      const key = el.dataset.i18n;
      if (translations && translations[key]) {
        el.textContent = translations[key];
      } else if (_originalText.has(key)) {
        el.textContent = _originalText.get(key);
      }
    });

    // Update nav links (data-i18n-nav)
    document.querySelectorAll('[data-i18n-nav]').forEach(el => {
      const key = el.dataset.i18nNav;
      if (translations && translations[key]) {
        el.textContent = translations[key];
      } else if (_originalText.has(key)) {
        el.textContent = _originalText.get(key);
      }
    });
  }

  // When lang is 'en' (English), the HTML already contains English text.
  // For Chinese, we use the i18n data above.
  document.querySelectorAll('.lang-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      setLanguage(btn.dataset.lang);
    });
  });

  // ================================================================
  // Mobile Menu
  // ================================================================
  const mobileMenuBtn = document.getElementById('mobile-menu-btn');
  const navLinks = document.getElementById('nav-links');
  const menuIcon = document.getElementById('menu-icon');

  if (mobileMenuBtn && navLinks) {
    mobileMenuBtn.addEventListener('click', () => {
      const isOpen = navLinks.classList.toggle('open');
      menuIcon.innerHTML = isOpen
        ? '<use href="#icon-close"/>'
        : '<use href="#icon-menu"/>';
      mobileMenuBtn.setAttribute('aria-expanded', isOpen);
    });

    // Close menu on link click (mobile)
    navLinks.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', () => {
        navLinks.classList.remove('open');
        menuIcon.innerHTML = '<use href="#icon-menu"/>';
        mobileMenuBtn.setAttribute('aria-expanded', 'false');
      });
    });

    // Close menu on outside click
    document.addEventListener('click', (e) => {
      if (!navLinks.contains(e.target) && !mobileMenuBtn.contains(e.target)) {
        navLinks.classList.remove('open');
        menuIcon.innerHTML = '<use href="#icon-menu"/>';
        mobileMenuBtn.setAttribute('aria-expanded', 'false');
      }
    });
  }

  // ================================================================
  // Nav Scroll Effect
  // ================================================================
  const nav = document.getElementById('nav');
  let lastScrollY = 0;

  function handleNavScroll() {
    const scrollY = window.scrollY;
    if (scrollY > 10) {
      nav.classList.add('scrolled');
    } else {
      nav.classList.remove('scrolled');
    }
    lastScrollY = scrollY;
  }

  // ================================================================
  // Back to Top
  // ================================================================
  const backToTop = document.getElementById('back-to-top');

  function handleBackToTop() {
    if (window.scrollY > 500) {
      backToTop.classList.add('visible');
    } else {
      backToTop.classList.remove('visible');
    }
  }

  if (backToTop) {
    backToTop.addEventListener('click', () => {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  // ================================================================
  // FAQ Accordion
  // ================================================================
  document.querySelectorAll('.faq-question').forEach(btn => {
    btn.addEventListener('click', () => {
      const item = btn.parentElement;
      const isOpen = item.classList.contains('open');

      // Close all others
      document.querySelectorAll('.faq-item.open').forEach(openItem => {
        if (openItem !== item) {
          openItem.classList.remove('open');
          openItem.querySelector('.faq-question').setAttribute('aria-expanded', 'false');
        }
      });

      // Toggle current
      item.classList.toggle('open', !isOpen);
      btn.setAttribute('aria-expanded', !isOpen);
    });
  });

  // ================================================================
  // Code Copy
  // ================================================================
  document.querySelectorAll('.code-copy-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const code = btn.closest('.code-block').querySelector('code').textContent;
      try {
        await navigator.clipboard.writeText(code);
        btn.classList.add('copied');
        const originalHTML = btn.innerHTML;
        btn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>';
        setTimeout(() => {
          btn.classList.remove('copied');
          btn.innerHTML = originalHTML;
        }, 2000);
      } catch (err) {
        // Fallback for older browsers
        const textarea = document.createElement('textarea');
        textarea.value = code;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        try {
          document.execCommand('copy');
          btn.classList.add('copied');
          setTimeout(() => btn.classList.remove('copied'), 2000);
        } catch (e) { /* Silently fail */ }
        document.body.removeChild(textarea);
      }
    });
  });

  // ================================================================
  // Scroll Animations (Intersection Observer)
  // ================================================================
  const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px',
  };

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }
    });
  }, observerOptions);

  // Observe elements for animations
  function setupAnimations() {
    const targets = [
      '.feature-card',
      '.plugin-card',
      '.qs-card',
      '.ss-card',
      '.tech-group',
      '.faq-item',
    ];

    targets.forEach(selector => {
      document.querySelectorAll(selector).forEach((el, index) => {
        el.classList.add('animate-in');
        el.style.transitionDelay = `${index * 0.06}s`;
        observer.observe(el);
      });
    });
  }

  // ================================================================
  // Scroll Event Handler (composed)
  // ================================================================
  let ticking = false;
  window.addEventListener('scroll', () => {
    if (!ticking) {
      requestAnimationFrame(() => {
        handleNavScroll();
        handleBackToTop();
        ticking = false;
      });
      ticking = true;
    }
  }, { passive: true });

  // ================================================================
  // Smooth scroll for anchor links (fallback for browsers without
  // native smooth scroll)
  // ================================================================
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
      const targetId = this.getAttribute('href');
      if (targetId === '#') return;
      const target = document.querySelector(targetId);
      if (target) {
        e.preventDefault();
        const navHeight = document.getElementById('nav').offsetHeight;
        const targetPosition = target.getBoundingClientRect().top + window.pageYOffset - navHeight;
        window.scrollTo({
          top: targetPosition,
          behavior: 'smooth',
        });
      }
    });
  });

  // ================================================================
  // Initialization
  // ================================================================
  function init() {
    _captureOriginalText();
    setLanguage('zh');  // 默认中文，必须在 _captureOriginalText() 之后
    handleNavScroll();
    handleBackToTop();
    setupAnimations();
  }

  // Run after DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
