import { useState, useEffect } from "react";
import { checkPageAccess } from "../utils/auth";

export default function ProtectedRoute({ page, children, user }) {
  const [hasAccess, setHasAccess] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkAccess = async () => {
      if (!user || !user.privileges || !Array.isArray(user.privileges)) {
        setHasAccess(false);
        setLoading(false);
        return;
      }

      // Check access both client-side (fast) and server-side (secure)
      const pagePrivilegeMap = {
        bulk: "bulk_operations",
        routers: "router_commands",
        history: "view_history",
        backups: "view_backups",
        reports: "manage_reports",
        generatereports: "manage_reports",
        credentials: "manage_credentials",
        admin: "admin_access",
      };

      const requiredPrivilege = pagePrivilegeMap[page];
      const clientSideAccess = requiredPrivilege
        ? user.privileges.includes(requiredPrivilege)
        : false;

      // Also verify server-side for security
      const serverSideAccess = await checkPageAccess(page);

      setHasAccess(clientSideAccess && serverSideAccess);
      setLoading(false);
    };

    checkAccess();
  }, [page, user]);

  if (loading) {
    return (
      <div style={{ padding: 40, textAlign: "center" }}>
        <p className="card-subtitle">Checking access...</p>
      </div>
    );
  }

  if (!hasAccess) {
    return (
      <div style={{ padding: 40, textAlign: "center" }}>
        <h2 className="app-main-title">Access Denied</h2>
        <p className="card-subtitle">
          You don't have permission to access this page. Please contact an
          administrator.
        </p>
      </div>
    );
  }

  return children;
}
