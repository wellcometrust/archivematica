from django.http import HttpResponse
from django.test import TestCase

from components import helpers

import mock


class TestProcessingConfig(TestCase):
    fixtures = ["test_user"]

    def setUp(self):
        self.client.login(username="test", password="test")
        helpers.set_setting("dashboard_uuid", "test-uuid")

    @mock.patch("components.administration.views_processing.os.path.isfile")
    def test_download_404(self, mock_is_file):
        mock_is_file.return_value = False
        response = self.client.get("/administration/processing/download/default/")
        self.assertEquals(response.status_code, 404)

    @mock.patch("components.helpers.send_file")
    @mock.patch("components.administration.views_processing.os.path.isfile")
    def test_download_ok(self, mock_is_file, mock_send_file):
        mock_is_file.return_value = True
        mock_send_file.return_value = HttpResponse(
            "<!DOCTYPE _[<!ELEMENT _ EMPTY>]><_/>"
        )
        response = self.client.get("/administration/processing/download/default/")
        self.assertEquals(response.content, "<!DOCTYPE _[<!ELEMENT _ EMPTY>]><_/>")

    @mock.patch(
        "components.administration.forms.MCPClient.get_processing_config_fields",
        return_value={},
    )
    def test_edit_new_config(self, mock_conf_fields):
        response = self.client.get("/administration/processing/add/")
        self.assertEquals(response.status_code, 200)
        self.assertNotIn("name", response.context["form"].initial)

    @mock.patch(
        "components.administration.forms.MCPClient.get_processing_config_fields",
        return_value={},
    )
    @mock.patch(
        "components.administration.forms.ProcessingConfigurationForm.load_config",
        side_effect=IOError(),
    )
    def test_edit_not_found_config(self, mock_load_config, mock_conf_fields):
        response = self.client.get("/administration/processing/edit/not_found_config/")
        self.assertEquals(response.status_code, 404)
        mock_load_config.assert_called_once_with("not_found_config")

    @mock.patch(
        "components.administration.forms.MCPClient.get_processing_config_fields",
        return_value={},
    )
    @mock.patch(
        "components.administration.forms.ProcessingConfigurationForm.load_config"
    )
    def test_edit_found_config(self, mock_load_config, mock_conf_fields):
        response = self.client.get("/administration/processing/edit/found_config/")
        self.assertEquals(response.status_code, 200)
        mock_load_config.assert_called_once_with("found_config")
