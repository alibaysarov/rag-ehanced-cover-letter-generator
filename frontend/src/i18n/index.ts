import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import ru from './locales/ru.json';
import en from './locales/en.json';

const savedLang = localStorage.getItem('aurora.uiLang');
const defaultLang = savedLang === 'ru' || savedLang === 'en' ? savedLang : 'ru';

i18n.use(initReactI18next).init({
  resources: { ru: { translation: ru }, en: { translation: en } },
  lng: defaultLang,
  fallbackLng: 'ru',
  interpolation: { escapeValue: false },
});

export default i18n;
