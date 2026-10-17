from shieldz.model.data import default_data_path, load_raw_df
import fastparquet

def test_fastparquet_load():
    p = default_data_path()
    print("Testing file:", p)
    pf = fastparquet.ParquetFile(str(p))
    print("Row count:", pf.count())
    print("Columns:", pf.columns)
    df = load_raw_df(p, nrows=100)
    print("Loaded df shape:", df.shape)
    assert len(df) == 100
