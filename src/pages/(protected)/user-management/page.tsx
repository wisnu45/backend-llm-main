import { Suspense, useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { ColumnDef } from '@tanstack/react-table';
import { useDebounce } from 'use-debounce';

import { DataTable } from '@/components/shared/data-table';
import { LoaderCircle } from '@/components/shared/loader';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea, ScrollBar } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';

import UserManagementHeader from './_components/user-management-header';
import UserManagementModals from './_components/user-management-modals';

import useGetUsers from './_hooks/get-users';
import useGetRoles from './_hooks/get-roles';

import { TUser, TRole } from '@/api/user-management/type';
import { formatDate } from '@/lib/date';

type TModal =
  | 'delete-user'
  | 'delete-role'
  | 'edit-user'
  | 'edit-role'
  | 'create-user'
  | 'create-role'
  | 'detail-user'
  | 'detail-role'
  | null;

const useUserManagementPage = () => {
  const [modal, setModal] = useState<TModal>(null);
  const [userData, setUserData] = useState<TUser | null>(null);
  const [roleData, setRoleData] = useState<TRole | null>(null);
  const [tab, setTab] = useState<'users' | 'roles'>('users');
  const [textSearch, setTextSearch] = useState<string>('');
  const [pageIndex, setPageIndex] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [debouncedValue] = useDebounce(textSearch, 1000);

  const [searchParams, setSearchParams] = useSearchParams();

  const handleSetModal = (
    modal: TModal,
    userData?: TUser | null,
    roleData?: TRole | null
  ) => {
    setModal(modal);
    if (userData !== undefined) setUserData(userData);
    if (roleData !== undefined) setRoleData(roleData);
  };

  const pageFromURL = searchParams.get('page')
    ? Number(searchParams.get('page'))
    : 0;
  const limitFromURL = searchParams.get('page_size')
    ? Number(searchParams.get('page_size'))
    : 10;

  useEffect(() => {
    setPageIndex(pageFromURL);
    setPageSize(limitFromURL);
  }, [searchParams]);

  const usersQuery = useGetUsers({
    search: debouncedValue,
    page: pageIndex + 1,
    page_size: pageSize
  });

  const rolesQuery = useGetRoles({
    search: debouncedValue,
    page: pageIndex + 1,
    page_size: pageSize
  });

  const updateURLParams = (newPageIndex: number, newPageSize: number) => {
    setSearchParams({
      page: newPageIndex.toString(),
      page_size: newPageSize.toString(),
      tab: tab
    });
  };

  useEffect(() => {
    setPageIndex(0);
  }, [textSearch, tab]);

  return {
    userData,
    roleData,
    modal,
    setModal: handleSetModal,
    tab,
    setTab,
    textSearch,
    setTextSearch,
    pageIndex,
    setPageIndex,
    pageSize,
    setPageSize,
    usersQuery,
    rolesQuery,
    updateURLParams
  };
};

const UserManagementPage = () => {
  const {
    modal,
    setModal,
    userData,
    roleData,
    tab,
    setTab,
    setTextSearch,
    pageIndex,
    setPageIndex,
    pageSize,
    setPageSize,
    usersQuery,
    rolesQuery,
    updateURLParams
  } = useUserManagementPage();

  const getUsersColumns = (
    setModal: (
      modal: TModal,
      userData?: TUser | null,
      roleData?: TRole | null
    ) => void,
    startFrom: number
  ): ColumnDef<TUser>[] => [
    {
      accessorKey: 'id',
      header: 'NO',
      cell: ({ row }) => <div>{row.index + 1}</div>
    },
    {
      accessorKey: 'name',
      header: 'Name',
      cell: ({ row }) => <div className="min-w-40">{row.getValue('name')}</div>
    },
    {
      accessorKey: 'username',
      header: 'Username',
      cell: ({ row }) => (
        <div className="min-w-48">{row.getValue('username')}</div>
      )
    },
    {
      accessorKey: 'is_portal',
      header: 'Portal User',
      cell: ({ row }) => (
        <div className="min-w-24">
          <span
            className={`inline-block rounded-lg px-2 py-1 text-xs ${
              row.original.is_portal
                ? 'bg-green-50 text-green-600'
                : 'bg-gray-50 text-gray-600'
            }`}
          >
            {row.original.is_portal ? 'Yes' : 'No'}
          </span>
        </div>
      )
    },
    {
      accessorKey: 'role',
      header: 'Role',
      cell: ({ row }) => (
        <div className="min-w-32">
          <span className="inline-block rounded-lg bg-blue-50 px-2 py-1 text-sm text-blue-600">
            {row.getValue('role') || '-'}
          </span>
        </div>
      )
    },
    {
      header: 'Action',
      cell: ({ row }) => (
        <div className="flex space-x-2">
          <Button
            variant="ghost"
            onClick={() => setModal('detail-user', row.original)}
          >
            View
          </Button>
          <Button
            variant="ghost"
            onClick={() => setModal('edit-user', row.original)}
          >
            Edit
          </Button>
          <Button
            variant="ghost"
            onClick={() => setModal('delete-user', row.original)}
          >
            Delete
          </Button>
        </div>
      )
    }
  ];

  const getRolesColumns = (
    setModal: (
      modal: TModal,
      userData?: TUser | null,
      roleData?: TRole | null
    ) => void,
    startFrom: number
  ): ColumnDef<TRole>[] => [
    {
      accessorKey: 'id',
      header: 'NO',
      cell: ({ row }) => <div>{row.index + 1}</div>
    },
    {
      accessorKey: 'name',
      header: 'Role Name',
      cell: ({ row }) => <div className="min-w-32">{row.getValue('name')}</div>
    },
    {
      accessorKey: 'description',
      header: 'Description',
      cell: ({ row }) => (
        <div className="min-w-48">{row.getValue('description')}</div>
      )
    },
    {
      accessorKey: 'is_local',
      header: 'Local',
      cell: ({ row }) => (
        <div className="min-w-20">
          <span
            className={`inline-block rounded-lg px-2 py-1 text-xs ${
              row.original.is_local
                ? 'bg-green-50 text-green-600'
                : 'bg-gray-50 text-gray-600'
            }`}
          >
            {row.original.is_local ? 'Yes' : 'No'}
          </span>
        </div>
      )
    },
    {
      accessorKey: 'is_portal',
      header: 'Portal',
      cell: ({ row }) => (
        <div className="min-w-20">
          <span
            className={`inline-block rounded-lg px-2 py-1 text-xs ${
              row.original.is_portal
                ? 'bg-blue-50 text-blue-600'
                : 'bg-gray-50 text-gray-600'
            }`}
          >
            {row.original.is_portal ? 'Yes' : 'No'}
          </span>
        </div>
      )
    },
    {
      header: 'Action',
      cell: ({ row }) => (
        <div className="flex space-x-2">
          <Button
            variant="ghost"
            onClick={() => setModal('detail-role', null, row.original)}
          >
            View
          </Button>
          <Button
            variant="ghost"
            onClick={() => setModal('edit-role', null, row.original)}
          >
            Edit
          </Button>
          <Button
            variant="ghost"
            onClick={() => setModal('delete-role', null, row.original)}
          >
            Delete
          </Button>
        </div>
      )
    }
  ];

  const currentQuery = tab === 'users' ? usersQuery : rolesQuery;
  const { page, page_size, total_pages, total } =
    currentQuery.data?.pagination || {};
  const startFrom = (Number(page) - 1) * Number(page_size);

  const usersColumns = getUsersColumns(setModal, startFrom);
  const rolesColumns = getRolesColumns(setModal, startFrom);

  const setInput = (value: React.ChangeEvent<HTMLInputElement>) => {
    setPageIndex(0);
    setTextSearch(value.target.value);
  };

  const handlePageChange = (newPageIndex: number) => {
    setPageIndex(newPageIndex);
    updateURLParams(newPageIndex, pageSize);
  };

  const handlePageSizeChange = (newPageSize: number) => {
    setPageSize(newPageSize);
    updateURLParams(pageIndex, newPageSize);
  };

  return (
    <div>
      <UserManagementHeader
        activeTab={tab}
        setModal={setModal}
        setInput={setInput}
      />

      <Tabs
        defaultValue="users"
        value={tab}
        onValueChange={(val) => {
          setTab(val as 'users' | 'roles');
          setPageIndex(0);
        }}
      >
        <ScrollArea className="w-full">
          <TabsList className="flex w-max min-w-full flex-row space-x-4">
            <TabsTrigger value="users" className="w-full sm:w-auto">
              Users
            </TabsTrigger>
            <TabsTrigger value="roles" className="w-full sm:w-auto">
              Role
            </TabsTrigger>
          </TabsList>
          <ScrollBar orientation="horizontal" />
        </ScrollArea>

        <TabsContent value="users">
          <Suspense fallback={<LoaderCircle />}>
            <DataTable
              pageCount={total_pages || 0}
              loading={usersQuery.isLoading}
              data={usersQuery.data?.data || []}
              columns={usersColumns}
              pageSizeOptions={[10, 20, 30, 40, 50]}
              setPageIndex={handlePageChange}
              pageIndex={pageIndex}
              setPageSize={handlePageSizeChange}
              total={total || 0}
              pageSize={page_size || 10}
            />
          </Suspense>
        </TabsContent>

        <TabsContent value="roles">
          <Suspense fallback={<LoaderCircle />}>
            <DataTable
              pageCount={total_pages || 0}
              loading={rolesQuery.isLoading}
              data={rolesQuery.data?.data || []}
              columns={rolesColumns}
              pageSizeOptions={[10, 20, 30, 40, 50]}
              setPageIndex={handlePageChange}
              pageIndex={pageIndex}
              setPageSize={handlePageSizeChange}
              total={total || 0}
              pageSize={page_size || 10}
            />
          </Suspense>
        </TabsContent>
      </Tabs>

      <UserManagementModals
        userData={userData}
        roleData={roleData}
        modal={modal}
        setModal={setModal}
      />
    </div>
  );
};

export default UserManagementPage;
