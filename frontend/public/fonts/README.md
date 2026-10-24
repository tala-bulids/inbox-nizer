# Local fonts

IBM Plex Mono Regular and SemiBold are self-hosted from the [official IBM Plex repository](https://github.com/IBM/plex/tree/master/packages/plex-mono/fonts/complete/woff2). The included IBM-Plex-LICENSE.txt is the SIL Open Font License. No runtime Google Fonts requests or CSP changes are required.

Arabic uses the Thmanyah Sans family when installed locally. A licensed distributable Thmanyah Sans font asset was not present in the project at integration time. Until supplied, Tahoma/Arial is the explicit fallback. Do not rename another font or claim the fallback is Thmanyah Sans. When a licensed webfont is supplied, add its local URL to the existing Thmanyah Sans @font-face in src/styles/theme.css and include the applicable license.
