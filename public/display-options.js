(function () {
  function shouldIncludeClasses(params) {
    return params.get("includeClasses") !== "false";
  }

  function buildFullscreenUrl(currentHref, options) {
    const url = new URL("./fullscreen.html", currentHref);
    url.searchParams.set("includeClasses", String(Boolean(options.includeClasses)));
    if (options.theme) {
      url.searchParams.set("theme", options.theme);
    }
    return url;
  }

  window.AcwDisplayOptions = {
    buildFullscreenUrl,
    shouldIncludeClasses
  };
}());
