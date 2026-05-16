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
      'nav.weekly_plan':   'Weekly Plan',
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

      // Dashboard dynamic content
      'dashboard.welcome_prefix':     'Welcome back,',
      'dashboard.acres':              'Acres',
      'dashboard.active':             'active',
      'dashboard.urgent':             'Urgent',
      'dashboard.healthy':            'Healthy',
      'dashboard.attention':          'Attention',
      'dashboard.soil_moisture':      'Soil Moisture',
      'dashboard.soil_heat':          'Soil Heat Gauge',
      'dashboard.overdue':            'Overdue',
      'dashboard.view_all':           'View All',
      'dashboard.all_clear':          'All clear — no urgent tasks.',
      'dashboard.no_active_crops':    'No active crops.',
      'dashboard.view_current_plan':  'View Current Plan',
      'dashboard.create_new_plan':    'Create New Plan',
      'dashboard.ready_to_map':       'Ready to map out the season?',
      'dashboard.seasonal_desc':      'Start your seasonal planning with our predictive yield models and soil health projections.',
      'dashboard.moisture_low':       'Low',
      'dashboard.moisture_high':      'High',
      'dashboard.moisture_optimal':   'Optimal',
      'dashboard.heat_cool':          'Cool',
      'dashboard.heat_hot':           'Hot',
      'dashboard.heat_warm':          'Warm',
      'dashboard.priority_critical':  'Critical',
      'dashboard.priority_high':      'High',
      'dashboard.priority_medium':    'Medium',
      'dashboard.priority_low':       'Low',

      // Common UI chrome
      'common.active':          'Active',
      'common.inactive':        'Inactive',
      'common.done':            'Done',
      'common.pending':         'Pending',
      'common.completed':       'Completed',
      'common.no_tasks':        'No tasks found.',
      'common.no_pending_tasks':'No pending tasks found.',
      'common.mark_done':       'Mark done',
      'common.mark_pending':    'Mark pending',
      'common.due_today':       'DUE TODAY',
      'common.loading':         'Loading…',
      'common.cancel':          'Cancel',
      'common.reset':           'Reset',
      'common.search':          'Search',
      'common.apply_filters':   'Apply Filters',
      'common.apply_sort':      'Apply Sort',
      'common.ascending':       'Ascending',
      'common.descending':      'Descending',
      'common.view_all':        'View All',
      'common.active_tasks':    'Active Tasks',
      'common.tasks_count':     'task',
      'common.tasks_count_pl':  'tasks',
      'common.no_crop':         'No Crop',

      // Fields page
      'fields.active_fields':     'Active Fields',
      'fields.all_fields':        'All Fields',
      'fields.view_all_inventory':'View All Field Inventory',
      'fields.pending_tasks':     'Pending Tasks',
      'fields.all_field_tasks':   'All Field Tasks',
      'fields.view_all_tasks':    'View All Field Tasks',
      'fields.no_active':         'No active fields found.',
      'fields.loading':           'Loading fields...',
      'fields.loading_all':       'Loading all fields...',
      'fields.loading_tasks':     'Loading tasks...',
      'fields.loading_all_tasks': 'Loading all tasks...',

      // Tasks page
      'tasks.pending_tasks':      'Pending Tasks',
      'tasks.all_tasks':          'All Tasks',
      'tasks.view_all':           'View All Tasks',
      'tasks.back_pending':       'Pending Tasks',
      'tasks.no_match':           'No tasks match your filters.',
      'tasks.loading_all':        'Loading all tasks...',
      'tasks.all_done':           'All tasks done — great work!',

      // Crops page
      'crops.active_crops':       'Active Crops',
      'crops.all_crops':          'All Crops',
      'crops.view_all_inventory': 'View All Crop Inventory',
      'crops.pending_tasks':      'Pending Tasks',
      'crops.all_crop_tasks':     'All Crop Tasks',
      'crops.view_all_tasks':     'View All Crop Tasks',
      'crops.no_active':          'No active crops found.',
      'crops.loading':            'Loading Crops...',
      'crops.loading_all':        'Loading all crops...',
      'crops.loading_tasks':      'Loading tasks...',
      'crops.loading_all_tasks':  'Loading all tasks...',

      // Button action titles
      'common.delete_field': 'Delete field',
      'common.edit_field':   'Edit field',
      'common.delete_crop':  'Delete crop',
      'common.edit_crop':    'Edit crop',
      'common.delete_task':  'Delete task',
      'common.edit_task':    'Edit task',

      // Health / status labels
      'status.healthy':  'Healthy',
      'status.alert':    'Alert',
      'status.critical': 'Critical',

      // Task type labels
      'task_type.irrigation':       'Irrigation',
      'task_type.spraying':         'Spraying',
      'task_type.harvesting':       'Harvesting',
      'task_type.pruning':          'Pruning',
      'task_type.pollination':      'Pollination',
      'task_type.defoliation':      'Defoliation',
      'task_type.fertilizing':      'Fertilizing',
      'task_type.soil_testing':     'Soil Testing',
      'task_type.drainage':         'Drainage',
      'task_type.plowing':          'Plowing',
      'task_type.weeding':          'Weeding',
      'task_type.land_preparation': 'Land Preparation',
      'task_type.maintenance':      'Maintenance',
      'task_type.inspection':       'Inspection',
      'task_type.equipment_check':  'Equipment Check',
      'task_type.planning':         'Planning',
      'task_type.monitoring':       'Monitoring',
      'task_type.default':          'Task',

      // Fields card tooltips & stats
      'fields.moisture_label':    'Moisture',
      'fields.temperature_label': 'Temperature',
      'fields.stress_high':       'High',
      'fields.stress_medium':     'Medium',
      'fields.stress_low':        'Low',
      'fields.threat_critical':   'Critical',
      'fields.threat_watch':      'Watch',
      'fields.threat_clear':      'Clear',
      'fields.health_no_fields':  'No active fields available.',
      'fields.health_critical':   'One or more active fields need urgent attention. Review moisture, stress, and disease indicators immediately.',
      'fields.health_alert':      'Some active fields show early warning signs. Monitor health trends and pending tasks closely.',
      'fields.health_ok':         'Average soil moisture and temperature levels across active fields are within a stable range.',

      // Common crop names (standardised terms — no API needed)
      'crop_name.wheat':      'Wheat',
      'crop_name.maize':      'Maize',
      'crop_name.corn':       'Corn',
      'crop_name.cotton':     'Cotton',
      'crop_name.rice':       'Rice',
      'crop_name.sugarcane':  'Sugarcane',
      'crop_name.sunflower':  'Sunflower',
      'crop_name.soybeans':   'Soybeans',
      'crop_name.soybean':    'Soybean',
      'crop_name.potato':     'Potato',
      'crop_name.tomato':     'Tomato',
      'crop_name.onion':      'Onion',
      'crop_name.chickpea':   'Chickpea',
      'crop_name.lentil':     'Lentil',
      'crop_name.mango':      'Mango',

      // Language toggle button text
      'lang.btn_label': 'اردو',
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
      'nav.weekly_plan':   'ہفتہ وار منصوبہ',
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

      // Dashboard dynamic content
      'dashboard.welcome_prefix':     'خوش آمدید،',
      'dashboard.acres':              'ایکڑ',
      'dashboard.active':             'فعال',
      'dashboard.urgent':             'فوری',
      'dashboard.healthy':            'صحت مند',
      'dashboard.attention':          'توجہ',
      'dashboard.soil_moisture':      'مٹی کی نمی',
      'dashboard.soil_heat':          'مٹی کی گرمی',
      'dashboard.overdue':            'باقی',
      'dashboard.view_all':           'سب دیکھیں',
      'dashboard.all_clear':          'سب ٹھیک ہے — کوئی فوری کام نہیں۔',
      'dashboard.no_active_crops':    'کوئی فعال فصل نہیں۔',
      'dashboard.view_current_plan':  'موجودہ منصوبہ دیکھیں',
      'dashboard.create_new_plan':    'نیا منصوبہ بنائیں',
      'dashboard.ready_to_map':       'موسم کی منصوبہ بندی کے لیے تیار ہیں؟',
      'dashboard.seasonal_desc':      'ہمارے پیش گوئی ماڈلز اور مٹی کی صحت کے تخمینوں سے موسمی منصوبہ بندی شروع کریں۔',
      'dashboard.moisture_low':       'کم',
      'dashboard.moisture_high':      'زیادہ',
      'dashboard.moisture_optimal':   'مناسب',
      'dashboard.heat_cool':          'ٹھنڈا',
      'dashboard.heat_hot':           'گرم',
      'dashboard.heat_warm':          'معتدل',
      'dashboard.priority_critical':  'نازک',
      'dashboard.priority_high':      'اعلی',
      'dashboard.priority_medium':    'درمیانی',
      'dashboard.priority_low':       'کم',

      // Common UI chrome
      'common.active':          'فعال',
      'common.inactive':        'غیر فعال',
      'common.done':            'مکمل',
      'common.pending':         'زیر التوا',
      'common.completed':       'مکمل',
      'common.no_tasks':        'کوئی کام نہیں ملا۔',
      'common.no_pending_tasks':'کوئی زیر التوا کام نہیں ملا۔',
      'common.mark_done':       'مکمل کریں',
      'common.mark_pending':    'زیر التوا کریں',
      'common.due_today':       'آج واجب',
      'common.loading':         'لوڈ ہو رہا ہے…',
      'common.cancel':          'منسوخ',
      'common.reset':           'ری سیٹ',
      'common.search':          'تلاش',
      'common.apply_filters':   'فلٹر لگائیں',
      'common.apply_sort':      'ترتیب لگائیں',
      'common.ascending':       'بڑھتا ہوا',
      'common.descending':      'گھٹتا ہوا',
      'common.view_all':        'سب دیکھیں',
      'common.active_tasks':    'فعال کام',
      'common.tasks_count':     'کام',
      'common.tasks_count_pl':  'کام',
      'common.no_crop':         'کوئی فصل نہیں',

      // Fields page
      'fields.active_fields':     'فعال کھیت',
      'fields.all_fields':        'تمام کھیت',
      'fields.view_all_inventory':'تمام کھیت دیکھیں',
      'fields.pending_tasks':     'زیر التوا کام',
      'fields.all_field_tasks':   'تمام کھیت کام',
      'fields.view_all_tasks':    'تمام کھیت کام دیکھیں',
      'fields.no_active':         'کوئی فعال کھیت نہیں ملا۔',
      'fields.loading':           'کھیت لوڈ ہو رہے ہیں...',
      'fields.loading_all':       'تمام کھیت لوڈ ہو رہے ہیں...',
      'fields.loading_tasks':     'کام لوڈ ہو رہے ہیں...',
      'fields.loading_all_tasks': 'تمام کام لوڈ ہو رہے ہیں...',

      // Tasks page
      'tasks.pending_tasks':      'زیر التوا کام',
      'tasks.all_tasks':          'تمام کام',
      'tasks.view_all':           'تمام کام دیکھیں',
      'tasks.back_pending':       'زیر التوا کام',
      'tasks.no_match':           'کوئی کام آپ کے فلٹر سے میل نہیں کھاتا۔',
      'tasks.loading_all':        'تمام کام لوڈ ہو رہے ہیں...',
      'tasks.all_done':           'تمام کام مکمل — شاندار!',

      // Crops page
      'crops.active_crops':       'فعال فصلیں',
      'crops.all_crops':          'تمام فصلیں',
      'crops.view_all_inventory': 'تمام فصلیں دیکھیں',
      'crops.pending_tasks':      'زیر التوا کام',
      'crops.all_crop_tasks':     'تمام فصل کام',
      'crops.view_all_tasks':     'تمام فصل کام دیکھیں',
      'crops.no_active':          'کوئی فعال فصل نہیں ملی۔',
      'crops.loading':            'فصلیں لوڈ ہو رہی ہیں...',
      'crops.loading_all':        'تمام فصلیں لوڈ ہو رہی ہیں...',
      'crops.loading_tasks':      'کام لوڈ ہو رہے ہیں...',
      'crops.loading_all_tasks':  'تمام کام لوڈ ہو رہے ہیں...',

      // Button action titles
      'common.delete_field': 'کھیت حذف کریں',
      'common.edit_field':   'کھیت ترمیم کریں',
      'common.delete_crop':  'فصل حذف کریں',
      'common.edit_crop':    'فصل ترمیم کریں',
      'common.delete_task':  'کام حذف کریں',
      'common.edit_task':    'کام ترمیم کریں',

      // Health / status labels
      'status.healthy':  'صحت مند',
      'status.alert':    'متنبہ',
      'status.critical': 'نازک',

      // Task type labels
      'task_type.irrigation':       'آبپاشی',
      'task_type.spraying':         'چھڑکاؤ',
      'task_type.harvesting':       'کٹائی',
      'task_type.pruning':          'کاٹ چھانٹ',
      'task_type.pollination':      'گرده برداری',
      'task_type.defoliation':      'پتے اتارنا',
      'task_type.fertilizing':      'کھاد ڈالنا',
      'task_type.soil_testing':     'مٹی کی جانچ',
      'task_type.drainage':         'نکاسی آب',
      'task_type.plowing':          'ہل چلانا',
      'task_type.weeding':          'گھاس پھوس صاف کرنا',
      'task_type.land_preparation': 'زمین کی تیاری',
      'task_type.maintenance':      'دیکھ بھال',
      'task_type.inspection':       'معائنہ',
      'task_type.equipment_check':  'آلات کی جانچ',
      'task_type.planning':         'منصوبہ بندی',
      'task_type.monitoring':       'نگرانی',
      'task_type.default':          'کام',

      // Fields card tooltips & stats
      'fields.moisture_label':    'نمی',
      'fields.temperature_label': 'درجہ حرارت',
      'fields.stress_high':       'زیادہ',
      'fields.stress_medium':     'درمیانی',
      'fields.stress_low':        'کم',
      'fields.threat_critical':   'نازک',
      'fields.threat_watch':      'نگرانی',
      'fields.threat_clear':      'محفوظ',
      'fields.health_no_fields':  'کوئی فعال کھیت دستیاب نہیں۔',
      'fields.health_critical':   'ایک یا زیادہ فعال کھیتوں کو فوری توجہ کی ضرورت ہے۔ نمی، دباؤ، اور بیماری کے اشارے فوری چیک کریں۔',
      'fields.health_alert':      'کچھ فعال کھیتوں میں ابتدائی انتباہی علامات ہیں۔ صحت کے رجحانات اور زیر التوا کاموں کی قریب سے نگرانی کریں۔',
      'fields.health_ok':         'فعال کھیتوں میں اوسط مٹی کی نمی اور درجہ حرارت مستحکم حد میں ہیں۔',

      // Common crop names
      'crop_name.wheat':      'گندم',
      'crop_name.maize':      'مکئی',
      'crop_name.corn':       'مکئی',
      'crop_name.cotton':     'کپاس',
      'crop_name.rice':       'چاول',
      'crop_name.sugarcane':  'گنا',
      'crop_name.sunflower':  'سورج مکھی',
      'crop_name.soybeans':   'سویا بین',
      'crop_name.soybean':    'سویا بین',
      'crop_name.potato':     'آلو',
      'crop_name.tomato':     'ٹماٹر',
      'crop_name.onion':      'پیاز',
      'crop_name.chickpea':   'چنا',
      'crop_name.lentil':     'دال',
      'crop_name.mango':      'آم',

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

  async function setLanguage(lang) {
    if (lang !== 'en' && lang !== 'ur') return;
    _lang = lang;
    localStorage.setItem('lang', lang);
    applyRTL();
    applyTranslations();
    updateLangToggle();
    if (typeof buildNav === 'function') buildNav();
    if (typeof renderConvList === 'function') renderConvList();
    // Pages expose prefetchAndRender(lang) to translate dynamic DB content before re-rendering.
    // Falls back to renderDashboard() for pages that don't need dynamic translation.
    if (typeof window.prefetchAndRender === 'function') {
      await window.prefetchAndRender(lang);
    } else if (typeof renderDashboard === 'function') {
      renderDashboard();
    }
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

  // ── Dynamic content translation (user-entered DB strings) ─────────────────
  var _DYN_KEY = 'i18n_dyn';

  // Translate a known crop name via the static dictionary before hitting the API.
  function translateCropName(name) {
    if (!name || _lang === 'en') return name;
    var key = 'crop_name.' + String(name).toLowerCase().trim();
    var val = T[_lang] && T[_lang][key];
    return (val && val !== key) ? val : getDynTranslation(name);
  }

  // Synchronous lookup from localStorage cache — call after translateDynamic resolves.
  function getDynTranslation(text) {
    if (!text || _lang === 'en') return text;
    try {
      var cache = JSON.parse(localStorage.getItem(_DYN_KEY) || '{}');
      return (cache[_lang] && cache[_lang][text]) || text;
    } catch (_) { return text; }
  }

  // Async — fetches uncached strings from /api/translate, merges into localStorage.
  async function translateDynamic(texts) {
    if (!texts || !texts.length || _lang === 'en') return {};
    try {
      var cache = JSON.parse(localStorage.getItem(_DYN_KEY) || '{}');
      var lc = cache[_lang] || {};
      var unique = [];
      var seen = {};
      texts.forEach(function(s) {
        if (s && s.trim() && !seen[s]) { seen[s] = true; unique.push(s); }
      });
      var uncached = unique.filter(function(s) { return !lc[s]; });
      if (uncached.length) {
        var res = await fetch('/api/translate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ texts: uncached, target: _lang }),
        });
        var data = await res.json();
        Object.assign(lc, data.translations || {});
        cache[_lang] = lc;
        localStorage.setItem(_DYN_KEY, JSON.stringify(cache));
      }
      return lc;
    } catch (e) {
      console.warn('Dynamic translation failed:', e);
      return {};
    }
  }

  // ── Exports ───────────────────────────────────────────────────────────────
  global.t                  = t;
  global.setLanguage        = setLanguage;
  global.toggleLanguage     = toggleLanguage;
  global.getCurrentLang     = getCurrentLang;
  global.getDynTranslation  = getDynTranslation;
  global.translateDynamic   = translateDynamic;
  global.translateCropName  = translateCropName;

})(window);
