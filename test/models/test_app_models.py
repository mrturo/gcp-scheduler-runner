def test_endpoint_config_invalid_type():
    """
    Test EndpointConfig.from_config with invalid type raises ValueError.
    """
    with pytest.raises(ValueError, match="Invalid endpoint configuration type"):
        EndpointConfig.from_config(12345)  # Pass an int instead of str or dict
