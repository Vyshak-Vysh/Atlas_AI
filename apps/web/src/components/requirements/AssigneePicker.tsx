"use client";

import { ChevronDown, UserX } from "lucide-react";

import { useProjectMembers } from "@/hooks/useTeam";
import { Avatar } from "@/components/ui/Avatar";
import { DropdownMenu, MenuItem, MenuSeparator } from "@/components/ui/DropdownMenu";

export function AssigneePicker({
  projectId,
  assigneeId,
  onChange,
  disabled,
}: {
  projectId: string;
  assigneeId: string | null;
  onChange: (userId: string | null) => void;
  disabled?: boolean;
}) {
  const { data: members } = useProjectMembers(projectId);
  const assignee = members?.find((m) => m.user_id === assigneeId);

  if (disabled) {
    return (
      <span style={{ display: "inline-flex", alignItems: "center", gap: "var(--space-2)", fontSize: "var(--font-size-sm)" }}>
        {assignee ? (
          <>
            <Avatar name={assignee.display_name} size={22} />
            {assignee.display_name}
          </>
        ) : (
          <span style={{ color: "var(--text-tertiary)" }}>Unassigned</span>
        )}
      </span>
    );
  }

  return (
    <DropdownMenu
      align="left"
      trigger={
        <button
          type="button"
          className="button button--secondary button--small"
          style={{ display: "inline-flex", alignItems: "center", gap: "var(--space-2)" }}
        >
          {assignee ? (
            <>
              <Avatar name={assignee.display_name} size={20} />
              {assignee.display_name}
            </>
          ) : (
            <>
              <UserX size={14} aria-hidden />
              Unassigned
            </>
          )}
          <ChevronDown size={14} aria-hidden />
        </button>
      }
    >
      {(members ?? []).map((member) => (
        <MenuItem key={member.user_id} onClick={() => onChange(member.user_id)} icon={<Avatar name={member.display_name} size={20} />}>
          {member.display_name}
        </MenuItem>
      ))}
      {assigneeId && (
        <>
          <MenuSeparator />
          <MenuItem onClick={() => onChange(null)} icon={<UserX size={14} aria-hidden />}>
            Unassign
          </MenuItem>
        </>
      )}
    </DropdownMenu>
  );
}
