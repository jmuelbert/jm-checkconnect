# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert
# test_url_checker.py

import configparser
import logging
import os
import pytest
import requests
from unittest.mock import mock_open, patch
from checkconnect.core.url_checker import URLChecker, translate

class TestURLChecker:
    @classmethod
    def setup_class(cls):
        cls.config_parser = configparser.ConfigParser()
        cls.config_parser.add_section('Network')
        cls.config_parser.set('Network', 'timeout', '5')

        cls.logger = logging.getLogger()
        cls.url_checker = URLChecker(cls.config_parser, cls.logger)

    def test_check_urls_file_not_found(self) -> None:
        with patch('builtins.open', mock_open()) as mocked_open:
            mocked_open.side_effect = FileNotFoundError
            result = self.url_checker.check_urls('non_existent_file.txt')
            expected_message = translate('URL file not found: non_existent_file.txt')
            assert result == [f"Error: {expected_message}"]

    def test_check_urls_read_error(self) -> None:
        with patch('builtins.open', mock_open()) as mocked_open:
            mocked_open.side_effect = Exception('read error')
            result = self.url_checker.check_urls('error_file.txt')
            expected_message = translate('Error reading URL file: read error')
            assert expected_message in result[0]

    def test_check_urls_no_urls(self) -> None:
        with patch('builtins.open', mock_open(read_data='')):
            result = self.url_checker.check_urls('empty_file.txt')
            expected_message = translate('No URLs found in the file.')
            assert result == [expected_message]

    def test_check_urls_success(self, mocker) -> None:
        url_data = 'http://example.com\nhttp://example.org\n'
        mock_response = mocker.Mock()
        mock_response.status_code = 200
        mocker.patch('requests.get', return_value=mock_response)
        
        with patch('builtins.open', mock_open(read_data=url_data)):
            results = self.url_checker.check_urls('urls.txt')
            assert len(results) == 2
            assert translate('URL: http://example.com - Status: 200') in results
            assert translate('URL: http://example.org - Status: 200') in results

    def test_check_urls_output_file(self, mocker) -> None:
        url_data = 'http://example.com\nhttp://example.org\n'
        mock_response = mocker.Mock()
        mock_response.status_code = 200
        mocker.patch('requests.get', return_value=mock_response)
        
        with patch('builtins.open', mock_open(read_data=url_data)) as mocked_open:
            with patch('builtins.open', mock_open()) as mocked_write_open:
                results = self.url_checker.check_urls('urls.txt', 'output.txt')
                mocked_write_open().write.assert_any_call(translate('URL: http://example.com - Status: 200') + '\n')
                mocked_write_open().write.assert_any_call(translate('URL: http://example.org - Status: 200') + '\n')

    def test_check_urls_request_exception(self, mocker) -> None:
        url_data = 'http://example.com\n'
        mocker.patch('requests.get', side_effect=requests.RequestException('request error'))
        
        with patch('builtins.open', mock_open(read_data=url_data)):
            results = self.url_checker.check_urls('urls.txt')
            assert len(results) == 1
            assert translate('Error checking URL http://example.com: request error') in results[0]

    def test_translations(self) -> None:
        assert translate('URL file not found: non_existent_file.txt') == 'URL file not found: non_existent_file.txt'
        assert translate('Error reading URL file: read error') == 'Error reading URL file: read error'
        assert translate('No URLs found in the file.') == 'No URLs found in the file.'
        assert translate('URL: http://example.com - Status: 200') == 'URL: http://example.com - Status: 200'
        assert translate('Error checking URL http://example.com: request error') == 'Error checking URL http://example.com: request error'
        assert translate('Results written to output.txt') == 'Results written to output.txt'
        assert translate('Error writing to output file: e') == 'Error writing to output file: e'
