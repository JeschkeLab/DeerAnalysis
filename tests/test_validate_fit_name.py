"""Checks validate_fit_name's duplicate detection and _<number> name suggestions."""
import tempfile

import pytest

from deeranalysis.utils import database as db
from deeranalysis.utils.database import Dataset, Fit
from deeranalysis.components.fit_page_components import validate_fit_name


@pytest.fixture()
def dataset_id():
    with tempfile.TemporaryDirectory() as tmp:
        db.init_db(tmp)
        session = db.get_session()
        ds = Dataset(name="d", project="p", sample="s", t=[0.0], V=[1.0])
        session.add(ds)
        session.flush()
        for name in ["fit", "fit_2", "fitx_9", "fit_a"]:
            session.add(Fit(dataset_id=ds.id, name=name, engine="DeerLab", t=[], model=[], r=[],
                            P_model=[], PUncert=[], fit_type="non-parametric", pathways=[1]))
        session.commit()
        yield ds.id
        session.close()
        db.engine.dispose()
        db.engine = None
        db.Session = None


def test_validate_fit_name(dataset_id):
    assert validate_fit_name("new", dataset_id) is True
    assert validate_fit_name("fit", dataset_id) is False
    assert validate_fit_name("new", dataset_id, suggest_new=True) == (True, "new")
    assert validate_fit_name("fit", dataset_id, suggest_new=True) == (False, "fit_3")
    assert validate_fit_name("fit_2", dataset_id, suggest_new=True) == (False, "fit_3")
