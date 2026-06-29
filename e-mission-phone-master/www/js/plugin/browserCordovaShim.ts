const isDesktopBrowser =
  typeof window !== 'undefined' &&
  window.location?.protocol?.startsWith('http') &&
  !window['cordova']?.plugins?.BEMUserCache;

function getLocalJson(key: string) {
  const raw = localStorage.getItem(key);
  return raw ? JSON.parse(raw) : null;
}

function setLocalJson(key: string, value: any) {
  localStorage.setItem(key, JSON.stringify(value));
  return Promise.resolve(value);
}

function getPromptedAuthToken() {
  return getLocalJson('prompted-auth')?.token || localStorage.getItem('browser_dev_opcode');
}

function getBrowserProfile() {
  const token = getPromptedAuthToken();
  if (token) localStorage.setItem('browser_dev_opcode', token);
  return {
    user_id: token || 'browser-dev-user',
    user_token: token || 'browser-dev-token',
    curr_platform: 'browser',
  };
}

function installBrowserCordovaShim() {
  if (!isDesktopBrowser) return;
  window['__BROWSER_CORDOVA_SHIM_READY'] = true;

  const cordova = (window['cordova'] = window['cordova'] || {});
  cordova.platformId = cordova.platformId || 'browser';
  cordova.plugins = cordova.plugins || {};
  cordova.plugin = cordova.plugin || {};

  cordova.plugin.http = cordova.plugin.http || {
    setDataSerializer: () => undefined,
    sendRequest: (_url, _options, success, _failure) => success?.({ data: '{}' }),
  };

  cordova.plugins.BEMUserCache = cordova.plugins.BEMUserCache || {
    getLocalStorage: (key) => Promise.resolve(getLocalJson(key)),
    putLocalStorage: (key, value) => setLocalJson(key, value),
    removeLocalStorage: (key) => {
      localStorage.removeItem(key);
      return Promise.resolve();
    },
    listAllLocalStorageKeys: () => Promise.resolve(Object.keys(localStorage)),
    listAllUniqueKeys: () => Promise.resolve([]),
    getDocument: (key) => Promise.resolve(getLocalJson(key)),
    putRWDocument: (key, value) => setLocalJson(key, value),
    putMessage: (key, value) => setLocalJson(key, value),
    getAllMessages: () => Promise.resolve([]),
    getMessagesForInterval: () => Promise.resolve([]),
    getSensorDataForInterval: () => Promise.resolve([]),
    getAllTimeQuery: () => ({}),
    clearAll: () => {
      localStorage.clear();
      return Promise.resolve();
    },
    invalidateAllCache: () => Promise.resolve(),
    isEmptyDoc: (doc) => !doc || Object.keys(doc).length === 0,
  };

  cordova.plugins.OPCodeAuth = cordova.plugins.OPCodeAuth || {
    getOPCode: () => Promise.resolve(getPromptedAuthToken()),
  };

  cordova.plugins.BEMServerComm = cordova.plugins.BEMServerComm || {
    getUserPersonalData: (path, success, _failure) => {
      if (path == '/profile/create' || path == '/profile/get') {
        success?.(getBrowserProfile());
      } else if (path == '/pipeline/get_range_ts') {
        success?.({ start_ts: null, end_ts: null });
      } else {
        success?.({});
      }
    },
    postUserPersonalData: (_path, _key, _value, success, _failure) => success?.({}),
    pushGetJSON: (_path, _msgFiller, success, _failure) => success?.({ phone_data: [] }),
  };

  cordova.plugins.BEMConnectionSettings = cordova.plugins.BEMConnectionSettings || {
    getDefaultSettings: () => Promise.resolve({}),
    setSettings: (settings) => Promise.resolve(settings),
  };

  cordova.plugins.BEMDataCollection = cordova.plugins.BEMDataCollection || {
    markConsented: (consent) => Promise.resolve(consent),
    getState: () => Promise.resolve({ curr_state: 'browser' }),
    isValidLocationSettings: () => Promise.resolve(false),
    isValidLocationPermissions: () => Promise.resolve(false),
    isValidFitnessPermissions: () => Promise.resolve(false),
    isValidBluetoothPermissions: () => Promise.resolve(false),
    isValidShowNotifications: () => Promise.resolve(false),
    isUnusedAppUnrestricted: () => Promise.resolve(true),
    isIgnoreBatteryOptimizations: () => Promise.resolve(true),
  };

  cordova.plugins.clipboard = cordova.plugins.clipboard || {
    paste: (callback) => callback(''),
  };

  cordova.plugins.barcodeScanner = cordova.plugins.barcodeScanner || {
    scan: (_success, failure) => failure?.('Barcode scanner is not available in browser preview'),
  };

  cordova.InAppBrowser = cordova.InAppBrowser || {
    open: (url) => window.open(url, '_blank'),
  };

  cordova.getAppVersion = cordova.getAppVersion || {
    getVersionNumber: () => Promise.resolve('browser-dev'),
  };

  setTimeout(() => document.dispatchEvent(new Event('deviceready')), 1000);
}

installBrowserCordovaShim();
