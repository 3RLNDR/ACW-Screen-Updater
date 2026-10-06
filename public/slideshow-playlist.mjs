export function buildStaticPlaylist(eventsPayload, videosPayload, includeClasses) {
  const eventSlides = (Array.isArray(eventsPayload?.items) ? eventsPayload.items : [])
    .filter((item) => includeClasses || !item.isClass)
    .map((item) => ({
      ...item,
      type: "event"
    }));

  const videoSlides = (Array.isArray(videosPayload?.videos) ? videosPayload.videos : [])
    .filter((video) => video?.src)
    .map((video, index) => ({
      type: "video",
      id: video.id || `video-${index + 1}`,
      title: video.title || "Video",
      src: video.src,
      durationSeconds: video.durationSeconds || 30
    }));

  return [...eventSlides, ...videoSlides];
}

export function findSlideIndex(items, currentSlide) {
  if (!currentSlide) {
    return -1;
  }

  const key = currentSlide.type === "video" ? currentSlide.id : currentSlide.link;
  if (!key) {
    return -1;
  }

  return items.findIndex((item) =>
    item.type === currentSlide.type && (item.type === "video" ? item.id : item.link) === key
  );
}
