interface User {
  id: string;
  username: string;
}

interface UserFilterDropdownProps {
  value: string | null;
  onChange: (userId: string | null) => void;
  users: User[];
}

export function UserFilterDropdown({
  value,
  onChange,
  users,
}: UserFilterDropdownProps) {
  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const selectedValue = e.target.value;
    onChange(selectedValue === "" ? null : selectedValue);
  };

  return (
    <select
      value={value ?? ""}
      onChange={handleChange}
      className="rounded-md border border-input bg-background px-3 py-2 text-sm"
      data-testid="user-filter-dropdown"
    >
      <option value="">All users</option>
      {users.map((user) => (
        <option key={user.id} value={user.id}>
          {user.username}
        </option>
      ))}
    </select>
  );
}
