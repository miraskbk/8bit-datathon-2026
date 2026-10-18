from tools.setup_local import configure


def test_setup_generates_private_key_and_preserves_existing_config(tmp_path):
    (tmp_path/'.env.example').write_text('API_KEY=replace-with-a-private-jury-key\nVLM_BACKEND=mlx\nVLM_MODEL=models/Qwen3-VL-8B-Instruct-4bit\n')
    assert configure(tmp_path,'transformers')
    original=(tmp_path/'.env').read_text()
    assert 'replace-with-a-private-jury-key' not in original
    assert 'VLM_BACKEND=transformers' in original
    assert (tmp_path/'.env').stat().st_mode & 0o777 == 0o600
    assert (tmp_path/'runtime/jury-access.txt').stat().st_mode & 0o777 == 0o600
    assert not configure(tmp_path,'mlx')
    assert (tmp_path/'.env').read_text()==original
