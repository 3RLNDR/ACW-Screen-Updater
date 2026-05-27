export function buildAssociationViewModel(events, videos, associations) {
  return events.map((event) => ({
    eventId: event.id,
    title: event.title || "Untitled event",
    dateText: event.dateText || "Date TBC",
    selectedVideoId: associations[event.id] || "",
    hasAssociation: Boolean(associations[event.id]),
    options: videos.map((video) => ({
      id: video.id,
      title: video.title || video.filename || video.id
    }))
  }));
}
