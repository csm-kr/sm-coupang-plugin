(() => {
  const rect = (element) => {
    if (!element) return null;
    const value = element.getBoundingClientRect();
    return {
      left: value.left + window.scrollX,
      right: value.right + window.scrollX,
      top: value.top + window.scrollY,
      bottom: value.bottom + window.scrollY,
      width: value.width,
      height: value.height,
    };
  };

  const positionValue = (token, axis) => {
    const normalized = String(token || "50%").toLowerCase();
    const keywords = axis === "x"
      ? {left: 0, center: 0.5, right: 1}
      : {top: 0, center: 0.5, bottom: 1};
    if (Object.hasOwn(keywords, normalized)) return keywords[normalized];
    if (normalized.endsWith("%")) return Math.min(1, Math.max(0, Number.parseFloat(normalized) / 100));
    return 0.5;
  };

  const sourceVisibleRect = (element) => {
    const style = getComputedStyle(element);
    const naturalWidth = Number(element.naturalWidth || element.videoWidth || 0);
    const naturalHeight = Number(element.naturalHeight || element.videoHeight || 0);
    const renderWidth = element.clientWidth;
    const renderHeight = element.clientHeight;
    if (!naturalWidth || !naturalHeight || !renderWidth || !renderHeight) {
      return {x: 0, y: 0, width: 0, height: 0};
    }
    const fit = style.objectFit || "fill";
    if (["contain", "fill", "none", "scale-down"].includes(fit)) {
      return {x: 0, y: 0, width: 1, height: 1};
    }
    const scale = Math.max(renderWidth / naturalWidth, renderHeight / naturalHeight);
    const visibleWidth = Math.min(naturalWidth, renderWidth / scale);
    const visibleHeight = Math.min(naturalHeight, renderHeight / scale);
    const tokens = style.objectPosition.trim().split(/\s+/);
    const px = positionValue(tokens[0], "x");
    const py = positionValue(tokens[1] || tokens[0], "y");
    const x = (naturalWidth - visibleWidth) * px;
    const y = (naturalHeight - visibleHeight) * py;
    return {
      x: x / naturalWidth,
      y: y / naturalHeight,
      width: visibleWidth / naturalWidth,
      height: visibleHeight / naturalHeight,
    };
  };

  const splitIds = (value) => String(value || "")
    .split(/[\s,]+/)
    .map((token) => token.trim())
    .filter(Boolean);

  const moduleElements = [...document.querySelectorAll("[data-module-id], [data-module]")];
  const modules = moduleElements.map((module, index) => {
    const assets = [...module.querySelectorAll("img[data-asset-id], video[data-asset-id]")].map((asset) => {
      const style = getComputedStyle(asset);
      return {
        id: asset.dataset.assetId,
        claim_ids: splitIds(asset.dataset.claimIds),
        natural_width: Number(asset.naturalWidth || asset.videoWidth || 0),
        natural_height: Number(asset.naturalHeight || asset.videoHeight || 0),
        render_width: asset.clientWidth,
        render_height: asset.clientHeight,
        rect: rect(asset),
        object_fit: style.objectFit,
        object_position: style.objectPosition,
        source_visible_rect: sourceVisibleRect(asset),
      };
    });
    const copy = module.querySelector(".module-copy, .hero-copy, .closing-copy, .spec-heading");
    const media = module.querySelector("figure, .media, .module-media, .overview-wrap, .motion-frame");
    return {
      id: module.dataset.moduleId || module.dataset.module || module.id,
      dom_order: index + 1,
      claim_ids: splitIds(module.getAttribute("data-claim-ids")),
      rect: rect(module),
      copy_rect: rect(copy),
      media_rect: rect(media),
      assets,
    };
  });
  return {
    schema_version: "1.0",
    width: window.innerWidth,
    height: window.innerHeight,
    device_pixel_ratio: window.devicePixelRatio,
    modules,
  };
})()
