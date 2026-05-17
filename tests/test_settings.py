from pathlib import Path

from dara.settings import DaraSettings


def test_structure_index_root_derives_database_paths(tmp_path):
    root = tmp_path / "Structure_index"
    config = tmp_path / "dara.yaml"
    config.write_text(f"PATH_TO_STRUCTURE_INDEX: {root.as_posix()}\n")

    settings = DaraSettings(CONFIG_FILE=str(config))

    assert settings.PATH_TO_STRUCTURE_INDEX == root
    assert settings.PATH_TO_COD == root / "cod_cifs"
    assert settings.PATH_TO_ICSD == root / "icsd_cifs"
    assert settings.PATH_TO_MP == root / "mp_cifs"


def test_explicit_database_paths_override_structure_index_root(tmp_path):
    root = tmp_path / "Structure_index"
    explicit_cod = tmp_path / "custom_cod"
    config = tmp_path / "dara.yaml"
    config.write_text(
        "\n".join(
            [
                f"PATH_TO_STRUCTURE_INDEX: {root.as_posix()}",
                f"PATH_TO_COD: {explicit_cod.as_posix()}",
            ]
        )
    )

    settings = DaraSettings(CONFIG_FILE=str(config))

    assert settings.PATH_TO_COD == explicit_cod
    assert settings.PATH_TO_ICSD == root / "icsd_cifs"
    assert settings.PATH_TO_MP == root / "mp_cifs"
