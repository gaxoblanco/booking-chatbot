"""
Analytics Service
=================
Handles all analytics and metrics tracking:
- Client search logging
- Professional contact tracking
- Metrics calculation
- Reporting and statistics
"""

from src.database.database import db
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json


class AnalyticsService:
    """
    Service layer for analytics operations.
    Tracks user behavior and calculates metrics.
    """

    def __init__(self):
        """Initialize analytics service."""
        self.db = db

    # ==========================================
    # SEARCH TRACKING
    # ==========================================

    def log_search(self, client_phone: str, search_type: str,
                   search_params: Dict, result_count: int,
                   session_id: str = None) -> Optional[int]:
        """
        Log a client search event.

        Args:
            client_phone: Client's WhatsApp number
            search_type: Type of search ('zona', 'fecha', 'prepaga', 'sexo', 'all')
            search_params: Dictionary with search parameters
            result_count: Number of results returned
            session_id: Session identifier for tracking flow

        Returns:
            Search ID if successful, None otherwise

        Example:
            >>> analytics.log_search(
            ...     "+5491112345678",
            ...     "zona",
            ...     {"zone": "norte", "prepaga": True},
            ...     5,
            ...     "session_abc123"
            ... )
            42
        """
        try:
            search_id = self.db.log_client_search(
                client_phone=client_phone,
                search_type=search_type,
                search_params=search_params,
                result_count=result_count,
                session_id=session_id
            )

            print(
                f"[ANALYTICS] ✅ Search logged: ID {search_id}, Type: {search_type}, Results: {result_count}")
            return search_id

        except Exception as e:
            print(f"[ANALYTICS] ❌ Error logging search: {e}")
            return None

    def mark_search_abandoned(self, search_id: int) -> bool:
        """
        Mark a search as abandoned (client didn't contact anyone).

        Args:
            search_id: Search record ID

        Returns:
            True if successful
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE client_searches 
                    SET search_abandoned = 1
                    WHERE id = ?
                """, (search_id,))

            print(f"[ANALYTICS] Search {search_id} marked as abandoned")
            return True

        except Exception as e:
            print(f"[ANALYTICS] ❌ Error marking search abandoned: {e}")
            return False

    # ==========================================
    # PROFESSIONAL INTERACTION TRACKING
    # ==========================================

    def log_professional_view(self, professional_phone: str) -> bool:
        """
        Increment view count when professional appears in search results.

        Args:
            professional_phone: Professional's phone

        Returns:
            True if successful
        """
        try:
            success = self.db.increment_professional_views(professional_phone)
            if success:
                print(f"[ANALYTICS] 👁️ View logged for: {professional_phone}")
            return success

        except Exception as e:
            print(f"[ANALYTICS] ❌ Error logging view: {e}")
            return False

    def log_profile_view(self, professional_phone: str) -> bool:
        """
        Increment profile view count when client views professional details.

        Args:
            professional_phone: Professional's phone

        Returns:
            True if successful
        """
        try:
            success = self.db.increment_profile_views(professional_phone)
            if success:
                print(
                    f"[ANALYTICS] 📋 Profile view logged for: {professional_phone}")
            return success

        except Exception as e:
            print(f"[ANALYTICS] ❌ Error logging profile view: {e}")
            return False

    def log_contact(self, search_id: int, professional_phone: str,
                    result_position: int = None) -> bool:
        """
        Log when client decides to contact a professional.
        Updates search record and professional metrics.

        Args:
            search_id: ID of search that led to contact
            professional_phone: Professional contacted
            result_position: Position in search results (1-based)

        Returns:
            True if successful
        """
        try:
            success = self.db.log_professional_contact(
                search_id=search_id,
                professional_phone=professional_phone,
                result_position=result_position
            )

            if success:
                print(
                    f"[ANALYTICS] 📞 Contact logged: {professional_phone} at position {result_position}")

            return success

        except Exception as e:
            print(f"[ANALYTICS] ❌ Error logging contact: {e}")
            return False

    def log_results_for_search(self, search_id: int, professional_phones: List[str]) -> bool:
        """
        Log all professionals shown in search results.
        Increments view count for each.

        Args:
            search_id: Search ID
            professional_phones: List of professional phones shown

        Returns:
            True if successful
        """
        try:
            for phone in professional_phones:
                self.log_professional_view(phone)

            print(
                f"[ANALYTICS] ✅ Logged views for {len(professional_phones)} professionals")
            return True

        except Exception as e:
            print(f"[ANALYTICS] ❌ Error logging result views: {e}")
            return False

    # ==========================================
    # METRICS CALCULATION
    # ==========================================

    def get_conversion_rate(self, days: int = 30) -> float:
        """
        Calculate conversion rate (searches that led to contact).

        Args:
            days: Number of days to look back (default 30)

        Returns:
            Conversion rate as percentage (0-100)
        """
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)
                           ).strftime("%Y-%m-%d %H:%M:%S")

            with self.db.get_connection() as conn:
                cursor = conn.cursor()

                # Total searches
                cursor.execute("""
                    SELECT COUNT(*) as total
                    FROM client_searches
                    WHERE created_at >= ?
                """, (cutoff_date,))
                total = cursor.fetchone()['total']

                if total == 0:
                    return 0.0

                # Searches with contact
                cursor.execute("""
                    SELECT COUNT(*) as converted
                    FROM client_searches
                    WHERE created_at >= ?
                    AND professional_contacted IS NOT NULL
                """, (cutoff_date,))
                converted = cursor.fetchone()['converted']

                rate = (converted / total) * 100
                print(
                    f"[ANALYTICS] Conversion rate (last {days} days): {rate:.2f}%")
                return rate

        except Exception as e:
            print(f"[ANALYTICS] ❌ Error calculating conversion rate: {e}")
            return 0.0

    def get_top_professionals(self, limit: int = 10, metric: str = 'contacts') -> List[Dict]:
        """
        Get top performing professionals.

        Args:
            limit: Number of results
            metric: Metric to rank by ('contacts', 'views', 'profile_views')

        Returns:
            List of professionals with metrics
        """
        try:
            metric_column = {
                'contacts': 'total_contacts',
                'views': 'total_views',
                'profile_views': 'total_profile_views'
            }.get(metric, 'total_contacts')

            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"""
                    SELECT 
                        phone,
                        name,
                        zone,
                        total_views,
                        total_profile_views,
                        total_contacts,
                        avg_search_position
                    FROM professionals
                    WHERE certificate_path IS NOT NULL
                    ORDER BY {metric_column} DESC
                    LIMIT ?
                """, (limit,))

                return [dict(row) for row in cursor.fetchall()]

        except Exception as e:
            print(f"[ANALYTICS] ❌ Error getting top professionals: {e}")
            return []

    def get_search_distribution(self, days: int = 30) -> Dict[str, int]:
        """
        Get distribution of search types.

        Args:
            days: Number of days to look back

        Returns:
            Dictionary with search type counts
        """
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)
                           ).strftime("%Y-%m-%d %H:%M:%S")

            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT search_type, COUNT(*) as count
                    FROM client_searches
                    WHERE created_at >= ?
                    GROUP BY search_type
                    ORDER BY count DESC
                """, (cutoff_date,))

                distribution = {}
                for row in cursor.fetchall():
                    distribution[row['search_type']] = row['count']

                return distribution

        except Exception as e:
            print(f"[ANALYTICS] ❌ Error getting search distribution: {e}")
            return {}

    def get_abandonment_rate(self, days: int = 30) -> float:
        """
        Calculate search abandonment rate.

        Args:
            days: Number of days to look back

        Returns:
            Abandonment rate as percentage (0-100)
        """
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)
                           ).strftime("%Y-%m-%d %H:%M:%S")

            with self.db.get_connection() as conn:
                cursor = conn.cursor()

                # Total searches
                cursor.execute("""
                    SELECT COUNT(*) as total
                    FROM client_searches
                    WHERE created_at >= ?
                """, (cutoff_date,))
                total = cursor.fetchone()['total']

                if total == 0:
                    return 0.0

                # Abandoned searches
                cursor.execute("""
                    SELECT COUNT(*) as abandoned
                    FROM client_searches
                    WHERE created_at >= ?
                    AND (search_abandoned = 1 OR professional_contacted IS NULL)
                """, (cutoff_date,))
                abandoned = cursor.fetchone()['abandoned']

                rate = (abandoned / total) * 100
                print(
                    f"[ANALYTICS] Abandonment rate (last {days} days): {rate:.2f}%")
                return rate

        except Exception as e:
            print(f"[ANALYTICS] ❌ Error calculating abandonment rate: {e}")
            return 0.0

    def get_avg_results_per_search(self, days: int = 30) -> float:
        """
        Calculate average number of results per search.

        Args:
            days: Number of days to look back

        Returns:
            Average number of results
        """
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)
                           ).strftime("%Y-%m-%d %H:%M:%S")

            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT AVG(result_count) as avg_results
                    FROM client_searches
                    WHERE created_at >= ?
                """, (cutoff_date,))

                result = cursor.fetchone()
                avg = result['avg_results'] if result['avg_results'] else 0.0

                print(
                    f"[ANALYTICS] Avg results per search (last {days} days): {avg:.2f}")
                return avg

        except Exception as e:
            print(f"[ANALYTICS] ❌ Error calculating avg results: {e}")
            return 0.0

    def get_professional_stats(self, professional_phone: str) -> Dict:
        """
        Get complete statistics for a professional.

        Args:
            professional_phone: Professional's phone

        Returns:
            Dictionary with all stats
        """
        try:
            prof = self.db.get_professional(professional_phone)
            if not prof:
                return {}

            stats = {
                'phone': prof['phone'],
                'name': prof['name'],
                'total_views': prof['total_views'],
                'total_profile_views': prof['total_profile_views'],
                'total_contacts': prof['total_contacts'],
                'avg_search_position': prof['avg_search_position'],
                'last_contacted_at': prof['last_contacted_at']
            }

            # Calculate conversion rates
            if prof['total_views'] > 0:
                stats['view_to_profile_rate'] = (
                    prof['total_profile_views'] / prof['total_views']) * 100
            else:
                stats['view_to_profile_rate'] = 0.0

            if prof['total_profile_views'] > 0:
                stats['profile_to_contact_rate'] = (
                    prof['total_contacts'] / prof['total_profile_views']) * 100
            else:
                stats['profile_to_contact_rate'] = 0.0

            return stats

        except Exception as e:
            print(f"[ANALYTICS] ❌ Error getting professional stats: {e}")
            return {}

    # ==========================================
    # REPORTS
    # ==========================================

    def generate_summary_report(self, days: int = 30) -> str:
        """
        Generate a summary analytics report.

        Args:
            days: Number of days to include

        Returns:
            Formatted report string
        """
        try:
            stats = self.db.get_stats()
            conversion = self.get_conversion_rate(days)
            abandonment = self.get_abandonment_rate(days)
            avg_results = self.get_avg_results_per_search(days)
            search_dist = self.get_search_distribution(days)
            top_pros = self.get_top_professionals(5, 'contacts')

            report = f"""
📊 ANALYTICS REPORT (Last {days} days)
{"="*50}

📈 GENERAL STATS:
   Total Professionals: {stats.get('total_professionals', 0)}
   Total Searches: {stats.get('total_searches', 0)}
   Total Contacts: {stats.get('total_contacts', 0)}

📊 PERFORMANCE:
   Conversion Rate: {conversion:.2f}%
   Abandonment Rate: {abandonment:.2f}%
   Avg Results/Search: {avg_results:.2f}

🔍 SEARCH TYPES:
"""
            for search_type, count in search_dist.items():
                report += f"   {search_type}: {count} searches\n"

            report += f"""
🏆 TOP 5 PROFESSIONALS (by contacts):
"""
            for idx, prof in enumerate(top_pros, 1):
                report += f"   {idx}. {prof['name']} - {prof['total_contacts']} contacts\n"

            report += f"\n{'='*50}\n"

            return report

        except Exception as e:
            print(f"[ANALYTICS] ❌ Error generating report: {e}")
            return "Error generating report"

    def generate_professional_report(self, professional_phone: str) -> str:
        """
        Generate a detailed report for a specific professional.

        Args:
            professional_phone: Professional's phone

        Returns:
            Formatted report string
        """
        try:
            stats = self.get_professional_stats(professional_phone)

            if not stats:
                return "Professional not found"

            report = f"""
👨‍⚕️ PROFESSIONAL REPORT: {stats['name']}
{"="*50}

📱 Contact: {stats['phone']}

📊 VISIBILITY:
   Total Views: {stats['total_views']}
   Profile Views: {stats['total_profile_views']}
   Contacts: {stats['total_contacts']}

📈 CONVERSION:
   View → Profile: {stats['view_to_profile_rate']:.2f}%
   Profile → Contact: {stats['profile_to_contact_rate']:.2f}%

🎯 RANKING:
   Avg Position in Results: {stats['avg_search_position']:.2f}

⏰ ACTIVITY:
   Last Contact: {stats['last_contacted_at'] or 'Never'}

{'='*50}
"""
            return report

        except Exception as e:
            print(f"[ANALYTICS] ❌ Error generating professional report: {e}")
            return "Error generating report"


# Global analytics service instance
analytics_service = AnalyticsService()
