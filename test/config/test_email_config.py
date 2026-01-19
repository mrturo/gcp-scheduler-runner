def test_email_notification_service_get_config():
    """
    Test EmailNotificationService.get_config returns the correct EmailConfig instance.
    """
    email_config = EmailConfig(
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_user="user@example.com",
        smtp_password="password",
        email_from="from@example.com",
        email_to="to@example.com",
    )
    service = EmailNotificationService(email_config)
    assert service.get_config() is email_config
