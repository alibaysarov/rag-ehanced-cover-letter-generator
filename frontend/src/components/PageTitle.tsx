import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useLocation } from 'react-router-dom'

const BRAND_NAME = 'FindJobFor.me'

const pageTitleKeys: Array<{ path: RegExp; key: string }> = [
  { path: /^\/$/, key: 'home' },
  { path: /^\/login$/, key: 'login' },
  { path: /^\/register$/, key: 'register' },
  { path: /^\/projects$/, key: 'projects' },
  { path: /^\/my-cvs$/, key: 'resumes' },
  { path: /^\/upload-cv$/, key: 'uploadResume' },
  { path: /^\/profile$/, key: 'profile' },
  { path: /^\/stats$/, key: 'statistics' },
  { path: /^\/auto-parse$/, key: 'autoParse' },
  { path: /^\/search-sites\/new$/, key: 'newSearchSite' },
  { path: /^\/search-sites\/\d+\/edit$/, key: 'editSearchSite' },
  { path: /^\/search-sites$/, key: 'searchSites' },
  { path: /^\/letter-constructor\/templates\/new$/, key: 'newLetterTemplate' },
  { path: /^\/letter-constructor\/templates\/\d+\/edit$/, key: 'editLetterTemplate' },
  { path: /^\/letter-constructor\/templates$/, key: 'letterTemplates' },
  { path: /^\/letter-constructor\/phrases$/, key: 'letterPhrases' },
]

function getPageTitleKey(pathname: string) {
  return pageTitleKeys.find(({ path }) => path.test(pathname))?.key ?? 'notFound'
}

export default function PageTitle() {
  const { pathname } = useLocation()
  const { t, i18n } = useTranslation()

  useEffect(() => {
    document.title = `${t(`pageTitle.${getPageTitleKey(pathname)}`)} | ${BRAND_NAME}`
  }, [i18n.language, pathname, t])

  return null
}
