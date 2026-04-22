from django.db.models.query import QuerySet

original_update = QuerySet.update

def debug_update(self, **kwargs):
    if "status" in kwargs:
        print("\n🚨 UPDATE CALLED:", kwargs)
        import traceback
        traceback.print_stack()
    return original_update(self, **kwargs)

QuerySet.update = debug_update