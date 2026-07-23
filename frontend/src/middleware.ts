import createMiddleware from "next-intl/middleware";
import { locales, defaultLocale } from "./locales";

export default createMiddleware({
  locales,
  defaultLocale,
  localePrefix: "as-needed",
});

export const config = {
  matcher: ["/((?!api|_next|.*\\..*).*)"],
};
