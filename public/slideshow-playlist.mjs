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
