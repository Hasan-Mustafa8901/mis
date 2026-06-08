import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { logActivity } from '../services/activityLogger';

export default function ActivityTracker() {
  const location = useLocation();

  useEffect(() => {
    logActivity('PAGE_VIEW', {
      path: location.pathname,
      search: location.search,
    });
  }, [location.pathname, location.search]);

  return null;
}