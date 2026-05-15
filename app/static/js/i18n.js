/**
 * AgriGemma — i18n module
 * Supports English (en) and Urdu (ur) with full RTL layout switching.
 *
 * Public API (attached to window):
 *   t(key)              — translate a key
 *   setLanguage(lang)   — switch to 'en' or 'ur'
 *   toggleLanguage()    — flip between the two
 *   getCurrentLang()    — returns current language code
 */
(function (global) {
  'use strict';

  // ── Translations ──────────────────────────────────────────────────────────
  var T = {
    en: {
      // App identity
      'app.subtitle': 'Climate Adaptation Planner',

      // Drawer navigation
      'nav.dashboard':     'Dashboard',
      'nav.crops':         'Crops',
      'nav.fields':        'Fields',
      'nav.tasks':         'Tasks',
      'nav.season_plan':   'Season Plan',
      'nav.chat':          'Chat',
      'nav.notifications': 'Notifications',

      // Chatbot UI
      'chat.welcome.title':     'How can I help today?',
      'chat.welcome.subtitle':  'Ask anything about your farm, or pick a topic below',
      'chat.new_conversation':  'New conversation',
      'chat.input.placeholder': 'Ask about your farm… (Enter to send)',
      'chat.powered_by':        'Powered by Gemma 4 · Runs locally on-device',
      'chat.loading':           'Loading…',
      'chat.no_conversations':  'No conversations yet.\nStart one above!',
      'chat.new_start':         'New conversation — ask me anything about your farm!',

      // Quick-prompt chip labels
      'chip.crop_health': 'Crop health',
      'chip.irrigation':  'Irrigation timing',
      'chip.pest':        'Pest management',
      'chip.planting':    'Planting advice',
      'chip.soil':        'Soil fertility',
      'chip.tasks':       'Task planning',

      // Quick-prompt text (sent to the AI)
      'prompt.crop_health': 'My crops look unhealthy — what could be wrong?',
      'prompt.irrigation':  'When should I irrigate my fields this week?',
      'prompt.pest':        'What are the best practices for pest and disease management?',
      'prompt.planting':    'What should I plant this season given current conditions?',
      'prompt.soil':        'How can I improve my soil fertility and health?',
      'prompt.tasks':       'What tasks should I prioritise on my farm this week?',

      // Date-group labels
      'group.today':     'Today',
      'group.yesterday': 'Yesterday',
      'group.this_week': 'This week',
      'group.older':     'Older',

      // Message-count plurals
      'msg.message':  'message',
      'msg.messages': 'messages',

      // Toasts & confirmations
      'error.load_convs':     'Could not load conversations',
      'error.delete_conv':    'Could not delete conversation',
      'error.message_failed': 'Message failed — check your connection',
      'error.start_conv':     'Failed to start a conversation',
      'error.load_conv':      'Failed to load conversation',
      'msg.conv_deleted':     'Conversation deleted',
      'confirm.delete_conv':  'Delete this conversation?',

      // Dashboard headings
      'dashboard.farm_overview':      'Farm Overview',
      'dashboard.optimal_range':      'Optimal Range',
      'dashboard.active_area':        'Active Area',
      'dashboard.crops_growing':      'Crops Growing',
      'dashboard.critical_tasks':     'Critical Tasks',
      'dashboard.crop_health_status': 'Crop Health Status',
      'dashboard.soil_conditions':    'Soil Conditions',

      // Language toggle button text
      'lang.btn_label': 'اردو',   // اردو
      'lang.btn_aria':  'Switch to Urdu',
    },

    ur: {
      // App identity
      'app.subtitle': 'موسم موافقت منصوبہ ساز',

      // Drawer navigation
      'nav.dashboard':     'ڈیش بورڈ',
      'nav.crops':         'فصلیں',
      'nav.fields':        'کھیت',
      'nav.tasks':         'کام',
      'nav.season_plan':   'موسمی منصوبہ',
      'nav.chat':          'چیٹ',
      'nav.notifications': 'اطلاعات',

      // Chatbot UI
      'chat.welcome.title':     'آج میں آپ کی کیا مدد کر سکتا ہوں؟',
      'chat.welcome.subtitle':  'اپنے کھیت کے بارے میں کچھ بھی پوچھیں، یا نیچے سے موضوع منتخب کریں',
      'chat.new_conversation':  'نئی گفتگو',
      'chat.input.placeholder': 'اپنے کھیت کے بارے میں پوچھیں… (بھیجنے کے لیے Enter دبائیں)',
      'chat.powered_by':        'جیما 4 سے تقویت یافتہ',
      'chat.loading':           'لوڈ ہو رہا ہے…',
      'chat.no_conversations':  'ابھی کوئی گفتگو نہیں۔\nاوپر سے نئی شروع کریں!',
      'chat.new_start':         'نئی گفتگو — اپنے کھیت کے بارے میں کچھ بھی پوچھیں!',

      // Quick-prompt chip labels
      'chip.crop_health': 'فصل کی صحت',
      'chip.irrigation':  'آبپاشی کا وقت',
      'chip.pest':        'کیڑوں کا انتظام',
      'chip.planting':    'کاشت کا مشورہ',
      'chip.soil':        'مٹی کی زرخیزی',
      'chip.tasks':       'کام کی منصوبہ بندی',

      // Quick-prompt text (sent to the AI)
      'prompt.crop_health': 'میری فصلیں صحت مند نہیں لگتیں — کیا مسئلہ ہو سکتا ہے؟',
      'prompt.irrigation':  'اس ہفتے میرے کھیتوں کو کب آبپاشی کرنی چاہیے؟',
      'prompt.pest':        'کیڑوں اور بیماریوں کے انتظام کے بہترین طریقے کیا ہیں؟',
      'prompt.planting':    'موجودہ حالات کے مطابق اس موسم میں کیا کاشت کروں؟',
      'prompt.soil':        'میں اپنی مٹی کی زرخیزی اور صحت کیسے بہتر کر سکتا ہوں؟',
      'prompt.tasks':       'اس ہفتے کھیت پر کون سے کاموں کو ترجیح دینی چاہیے؟',

      // Date-group labels
      'group.today':     'آج',
      'group.yesterday': 'کل',
      'group.this_week': 'اس ہفتے',
      'group.older':     'پرانے',

      // Message-count
      'msg.message':  'پیغام',
      'msg.messages': 'پیغامات',

      // Toasts & confirmations
      'error.load_convs':     'گفتگو لوڈ نہیں ہو سکی',
      'error.delete_conv':    'گفتگو حذف نہیں ہو سکی',
      'error.message_failed': 'پیغام ناکام رہا — انٹرنیٹ چیک کریں',
      'error.start_conv':     'گفتگو شروع نہیں ہو سکی',
      'error.load_conv':      'گفتگو لوڈ نہیں ہو سکی',
      'msg.conv_deleted':     'گفتگو حذف کر دی گئی',
      'confirm.delete_conv':  'کیا آپ یہ گفتگو حذف کرنا چاہتے ہیں؟',

      // Dashboard headings
      'dashboard.farm_overview':      'کھیت کا جائزہ',
      'dashboard.optimal_range':      'بہترین حد',
      'dashboard.active_area':        'فعال رقبہ',
      'dashboard.crops_growing':      'اگنے والی فصلیں',
      'dashboard.critical_tasks':     'ضروری کام',
      'dashboard.crop_health_status': 'فصل کی صحت کی حالت',
      'dashboard.soil_conditions':    'مٹی کی حالت',

      // Language toggle button text
      'lang.btn_label': 'EN',
      'lang.btn_aria':  'Switch to English',
    }
  };

  // ── Core state ────────────────────────────────────────────────────────────
  var _lang = localStorage.getItem('lang') || 'en';

  function t(key) {
    return (T[_lang] && T[_lang][key]) || (T.en[key]) || key;
  }

  function applyRTL() {
    var rtl = (_lang === 'ur');
    document.documentElement.setAttribute('dir',  rtl ? 'rtl' : 'ltr');
    document.documentElement.setAttribute('lang', rtl ? 'ur'  : 'en');
  }

  function applyTranslations() {
    document.querySelectorAll('[data-i18n]').forEach(function (el) {
      var key = el.getAttribute('data-i18n');
      var val = t(key);
      var tag = el.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA') {
        el.placeholder = val;
      } else {
        el.textContent = val;
      }
    });
  }

  function updateLangToggle() {
    var btn = document.getElementById('langToggleBtn');
    if (!btn) return;
    btn.textContent = t('lang.btn_label');
    btn.setAttribute('aria-label', t('lang.btn_aria'));
  }

  function setLanguage(lang) {
    if (lang !== 'en' && lang !== 'ur') return;
    _lang = lang;
    localStorage.setItem('lang', lang);
    applyRTL();
    applyTranslations();
    updateLangToggle();
    // Rebuild dynamic nav if present
    if (typeof buildNav === 'function') buildNav();
    // Re-render conversation list (date-group labels change)
    if (typeof renderConvList === 'function') renderConvList();
  }

  function toggleLanguage() {
    setLanguage(_lang === 'en' ? 'ur' : 'en');
  }

  function getCurrentLang() {
    return _lang;
  }

  // ── Boot ──────────────────────────────────────────────────────────────────
  // applyRTL() runs immediately so the page is never laid out in the wrong direction.
  applyRTL();

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      applyTranslations();
      updateLangToggle();
    });
  } else {
    applyTranslations();
    updateLangToggle();
  }

  // ── Exports ───────────────────────────────────────────────────────────────
  global.t              = t;
  global.setLanguage    = setLanguage;
  global.toggleLanguage = toggleLanguage;
  global.getCurrentLang = getCurrentLang;

})(window);
