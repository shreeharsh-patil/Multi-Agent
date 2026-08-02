"""Database helpers for Beanie document collections.

Beanie 1.x exposes ``get_motor_collection()`` while Beanie 2.x renamed it to
``get_pymongo_collection()``. Since ``beanie>=1.27.0`` may resolve to either,
these helpers keep collection access working across versions.
"""


def get_motor_collection(document_cls):
    """Return the underlying async collection for a Beanie document class.

    Compatible with both Beanie 1.x (``get_motor_collection``) and Beanie 2.x
    (``get_pymongo_collection``). The returned collection supports ``await``
    based queries (``find_one``, ``update_many``, etc.).
    """
    method = (
        getattr(document_cls, "get_pymongo_collection", None)
        or getattr(document_cls, "get_motor_collection", None)
    )
    if method is None:
        raise AttributeError(f"{document_cls.__name__} exposes no collection accessor")
    return method()
