from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import RoomTenant, Room


def _recompute_room_occupancy_and_status(room: Room) -> None:
    active_occupants = RoomTenant.objects.filter(room=room, status='active').count()
    room.current_occupants = active_occupants
    room.update_status()


@receiver(post_save, sender=RoomTenant)
def handle_roomtenant_saved(sender, instance: RoomTenant, created, **kwargs):
    _recompute_room_occupancy_and_status(instance.room)


@receiver(post_delete, sender=RoomTenant)
def handle_roomtenant_deleted(sender, instance: RoomTenant, **kwargs):
    _recompute_room_occupancy_and_status(instance.room)


