export function getNextRenderableSlide(slides, startIndex, failedVideoIds = new Set()) {
  for (let offset = 0; offset < slides.length; offset += 1) {
    const slide = slides[(startIndex + offset) % slides.length];
    if (slide.type !== "video") {
      return slide;
    }
    if (!failedVideoIds.has(slide.id) && slide.src) {
      return slide;
    }
  }

  return slides[startIndex] || null;
}
