from app.db import models
from app.db.session import session_factory


def test_dataset_persist_and_read() -> None:
    with session_factory() as s:
        ds = models.Dataset(
            original_filename="sample.csv",
            storage_key="uploads/sample.csv",
            file_size_bytes=1234,
            status="uploaded",
        )
        s.add(ds)
        s.commit()
        ds_id = ds.id

    with session_factory() as s:
        loaded = s.get(models.Dataset, ds_id)
        assert loaded is not None
        assert loaded.original_filename == "sample.csv"
        assert loaded.status == "uploaded"


def test_dataset_column_relationship() -> None:
    with session_factory() as s:
        ds = models.Dataset(
            original_filename="x.csv", storage_key="k", file_size_bytes=1
        )
        ds.columns.append(
            models.DatasetColumn(
                name="price",
                position=0,
                inferred_type="float",
                null_count=0,
                unique_count=10,
            )
        )
        s.add(ds)
        s.commit()
        assert len(ds.columns) == 1
        assert ds.columns[0].name == "price"
