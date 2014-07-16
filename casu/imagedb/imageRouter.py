class Router(object):
    def db_for_read(self, model, **hints):
        if model._meta.db_table == "imagedb_image":
            return "imagedb"
        return None
        
    def db_for_write(self, model, **hints):
        if model._meta.db_table == "imagedb_image":
            return "imagedb"
        return None
        
        