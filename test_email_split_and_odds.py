"""
Tests for:
  1. min_odds_threshold filtering (skip matches with odds < 1.19)
  2. skip_no_odds filtering (skip matches without odds)
  3. send_split_emails_by_sport grouping logic (2 emails per sport)
"""

import os
import pandas as pd
from typing import Any
from unittest.mock import patch, MagicMock

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_MATCHES: list[dict[str, Any]] = [
    # football, form_advantage=True, good odds
    dict(sport='football', home_team='Barcelona', away_team='Real Madrid',
         qualifies=True, form_advantage=True,
         home_odds=1.75, away_odds=4.20, match_time='2026-03-08 20:00'),
    # football, form_advantage=False, good odds
    dict(sport='football', home_team='Arsenal', away_team='Chelsea',
         qualifies=True, form_advantage=False,
         home_odds=2.10, away_odds=3.40, match_time='2026-03-08 18:00'),
    # football, form_advantage=True, LOW odds (home < 1.19)
    dict(sport='football', home_team='Bayern', away_team='Augsburg',
         qualifies=True, form_advantage=True,
         home_odds=1.10, away_odds=8.50, match_time='2026-03-08 15:30'),
    # football, qualifies but NO odds
    dict(sport='football', home_team='Dortmund', away_team='Mainz',
         qualifies=True, form_advantage=False,
         home_odds=None, away_odds=None, match_time='2026-03-08 15:30'),
    # basketball, form_advantage=True, good odds
    dict(sport='basketball', home_team='Lakers', away_team='Celtics',
         qualifies=True, form_advantage=True,
         home_odds=1.90, away_odds=1.95, match_time='2026-03-08 02:00'),
    # basketball, form_advantage=False, good odds
    dict(sport='basketball', home_team='Warriors', away_team='Nets',
         qualifies=True, form_advantage=False,
         home_odds=1.55, away_odds=2.50, match_time='2026-03-08 01:00'),
    # tennis, form_advantage=False, odds exactly 1.19 (edge case — should PASS)
    dict(sport='tennis', home_team='Djokovic', away_team='Nadal',
         qualifies=True, form_advantage=False,
         home_odds=1.19, away_odds=5.00, match_time='2026-03-08 14:00'),
    # not qualifying — should never appear
    dict(sport='football', home_team='Wolves', away_team='Brighton',
         qualifies=False, form_advantage=False,
         home_odds=2.00, away_odds=3.50, match_time='2026-03-08 16:00'),
]


def _write_csv(tmp_path: Any, matches: list[dict[str, Any]] | None = None) -> str:
    """Write sample matches to a temp CSV and return path."""
    df = pd.DataFrame(matches or SAMPLE_MATCHES)
    csv_path = os.path.join(str(tmp_path), 'test_matches.csv')
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    return csv_path


# ---------------------------------------------------------------------------
# Tests: min_odds_threshold in send_email_notification
# ---------------------------------------------------------------------------

class TestMinOddsThreshold:
    """send_email_notification should drop matches with any key odds < threshold."""

    @patch('email_notifier.smtplib.SMTP')
    def test_filters_low_odds(self, mock_smtp: Any, tmp_path: Any) -> None:
        from email_notifier import send_email_notification
        csv = _write_csv(tmp_path)

        # Capture what gets rendered by intercepting create_html_email
        with patch('email_notifier.create_html_email', return_value='<html>ok</html>') as mock_html:
            send_email_notification(
                csv_file=csv, to_email='a@b.com', from_email='a@b.com',
                password='x', skip_no_odds=True, min_odds_threshold=1.19,
            )
            # Bayern (1.10) and Dortmund (None) should be dropped
            matches_sent = mock_html.call_args[0][0]
            teams = {m['home_team'] for m in matches_sent}
            assert 'Bayern' not in teams, "Bayern (odds 1.10) should be filtered"
            assert 'Dortmund' not in teams, "Dortmund (no odds) should be filtered"
            assert 'Barcelona' in teams
            assert 'Djokovic' in teams, "Djokovic (odds exactly 1.19) should pass"

    @patch('email_notifier.smtplib.SMTP')
    def test_threshold_zero_means_no_filter(self, mock_smtp: Any, tmp_path: Any) -> None:
        from email_notifier import send_email_notification
        csv = _write_csv(tmp_path)

        with patch('email_notifier.create_html_email', return_value='<html>ok</html>') as mock_html:
            send_email_notification(
                csv_file=csv, to_email='a@b.com', from_email='a@b.com',
                password='x', skip_no_odds=False, min_odds_threshold=0.0,
            )
            matches_sent = mock_html.call_args[0][0]
            teams = {m['home_team'] for m in matches_sent}
            # With threshold 0 and skip_no_odds=False, all qualifying should pass
            assert 'Bayern' in teams
            assert 'Dortmund' in teams

    @patch('email_notifier.smtplib.SMTP')
    def test_no_matches_after_filter(self, mock_smtp: Any, tmp_path: Any) -> None:
        """If all matches are below threshold, no email should be sent."""
        from email_notifier import send_email_notification
        low = [dict(sport='football', home_team='A', away_team='B',
                    qualifies=True, form_advantage=False,
                    home_odds=1.05, away_odds=1.10, match_time='2026-03-08 12:00')]
        csv = _write_csv(tmp_path, low)

        send_email_notification(
            csv_file=csv, to_email='a@b.com', from_email='a@b.com',
            password='x', skip_no_odds=True, min_odds_threshold=1.19,
        )
        # SMTP should never be used (no matches to send)
        mock_smtp.return_value.__enter__.return_value.send_message.assert_not_called()


# ---------------------------------------------------------------------------
# Tests: send_split_emails_by_sport
# ---------------------------------------------------------------------------

class TestSplitEmailsBySport:
    """send_split_emails_by_sport should group by sport, then form_advantage."""

    @patch('email_notifier.smtplib.SMTP')
    def test_sends_correct_number_of_emails(self, mock_smtp: Any, tmp_path: Any) -> None:
        from email_notifier import send_split_emails_by_sport
        csv = _write_csv(tmp_path)

        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

        count = send_split_emails_by_sport(
            csv_file=csv, to_email='a@b.com', from_email='a@b.com',
            password='x', min_odds_threshold=1.19,
        )

        # Expected emails after filtering (Bayern dropped, Dortmund dropped):
        #   football: form_adv=[Barcelona] → 1 email, normal=[Arsenal] → 1 email = 2
        #   basketball: form_adv=[Lakers] → 1, normal=[Warriors] → 1 = 2
        #   tennis: form_adv=[], normal=[Djokovic] → 1 = 1
        # Total = 5
        assert count == 5
        assert mock_server.send_message.call_count == 5

    @patch('email_notifier.smtplib.SMTP')
    def test_subjects_contain_sport_and_type(self, mock_smtp: Any, tmp_path: Any) -> None:
        from email_notifier import send_split_emails_by_sport
        csv = _write_csv(tmp_path)

        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

        send_split_emails_by_sport(
            csv_file=csv, to_email='a@b.com', from_email='a@b.com',
            password='x', min_odds_threshold=1.19,
        )

        subjects: list[str] = []
        for c in mock_server.send_message.call_args_list:
            msg = c[0][0]
            subjects.append(str(msg['Subject']))

        # Check basketball form email exists
        bball_form = [s for s in subjects if 'Koszykówka' in s and 'PRZEWAGĄ FORMY' in s]
        assert len(bball_form) == 1
        # Check tennis normal email exists
        tennis_normal = [s for s in subjects if 'Tenis' in s and 'zwykłych' in s]
        assert len(tennis_normal) == 1

    @patch('email_notifier.smtplib.SMTP')
    def test_empty_group_not_sent(self, mock_smtp: Any, tmp_path: Any) -> None:
        """If a sport has no form_advantage matches, only 1 email for that sport."""
        from email_notifier import send_split_emails_by_sport
        only_normal = [
            dict(sport='hockey', home_team='A', away_team='B',
                 qualifies=True, form_advantage=False,
                 home_odds=2.00, away_odds=3.00, match_time='2026-03-08 19:00'),
        ]
        csv = _write_csv(tmp_path, only_normal)

        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

        count = send_split_emails_by_sport(
            csv_file=csv, to_email='a@b.com', from_email='a@b.com',
            password='x', min_odds_threshold=1.19,
        )
        assert count == 1  # only normal group

    @patch('email_notifier.smtplib.SMTP')
    def test_all_filtered_returns_zero(self, mock_smtp: Any, tmp_path: Any) -> None:
        from email_notifier import send_split_emails_by_sport
        low = [dict(sport='football', home_team='X', away_team='Y',
                    qualifies=True, form_advantage=True,
                    home_odds=1.05, away_odds=1.10, match_time='2026-03-08 12:00')]
        csv = _write_csv(tmp_path, low)

        count = send_split_emails_by_sport(
            csv_file=csv, to_email='a@b.com', from_email='a@b.com',
            password='x', min_odds_threshold=1.19,
        )
        assert count == 0

    @patch('email_notifier.smtplib.SMTP')
    def test_odds_exactly_threshold_passes(self, mock_smtp: Any, tmp_path: Any) -> None:
        """Odds == 1.19 should pass the filter."""
        from email_notifier import send_split_emails_by_sport
        edge = [dict(sport='tennis', home_team='Player1', away_team='Player2',
                     qualifies=True, form_advantage=False,
                     home_odds=1.19, away_odds=1.19, match_time='2026-03-08 10:00')]
        csv = _write_csv(tmp_path, edge)

        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

        count = send_split_emails_by_sport(
            csv_file=csv, to_email='a@b.com', from_email='a@b.com',
            password='x', min_odds_threshold=1.19,
        )
        assert count == 1

    @patch('email_notifier.smtplib.SMTP')
    def test_nan_string_odds_filtered(self, mock_smtp: Any, tmp_path: Any) -> None:
        """String 'NaN' odds should be treated as missing."""
        from email_notifier import send_split_emails_by_sport
        nans = [dict(sport='football', home_team='TeamA', away_team='TeamB',
                     qualifies=True, form_advantage=True,
                     home_odds='NaN', away_odds='NaN', match_time='2026-03-08 12:00')]
        csv = _write_csv(tmp_path, nans)

        count = send_split_emails_by_sport(
            csv_file=csv, to_email='a@b.com', from_email='a@b.com',
            password='x', min_odds_threshold=1.19,
        )
        assert count == 0
