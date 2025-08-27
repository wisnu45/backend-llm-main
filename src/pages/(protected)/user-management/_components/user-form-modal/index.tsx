import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog';
import { useForm } from 'react-hook-form';
import { UserFormSchema, TUserFormData } from './schema';
import { zodResolver } from '@hookform/resolvers/zod';
import { Input } from '@/components/ui/input';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage
} from '@/components/ui/form';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { useEffect } from 'react';
import {
  TRequestCreateUser,
  TRequestUpdateUser
} from '@/api/user-management/type';
import { Loader2 } from 'lucide-react';
import useGetRoles from '../../_hooks/get-roles';

interface Props {
  loading?: boolean;
  open?: boolean;
  onOpenChange: () => void;
  mode: 'create' | 'edit';
  defaultValues?: Partial<TUserFormData>;
  onSubmit: (data: TRequestCreateUser | TRequestUpdateUser) => void;
}

const UserFormModal = ({
  defaultValues,
  open,
  onOpenChange,
  onSubmit,
  mode,
  loading
}: Props) => {
  const metaMap: Record<Props['mode'], { title: string; desc: string }> = {
    create: {
      title: 'Add New User',
      desc: 'Create a new user account with assigned role.'
    },
    edit: {
      title: 'Edit User',
      desc: 'Update user information and role assignment.'
    }
  };

  const form = useForm<TUserFormData>({
    mode: 'onChange',
    resolver: zodResolver(UserFormSchema)
  });

  const rolesQuery = useGetRoles();
  const roles = rolesQuery.data?.data || [];

  const handleSubmit = (data: TUserFormData) => {
    onSubmit(data);
  };

  useEffect(() => {
    if (defaultValues) {
      form.reset(defaultValues);
    } else {
      form.reset({
        name: '',
        email: '',
        role_id: ''
      });
    }
  }, [defaultValues, form, open]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="no-scrollbar sm:max-w-md"
        onInteractOutside={(e) => e.preventDefault()}
        onOpenAutoFocus={(e) => e.preventDefault()}
      >
        <DialogHeader>
          <DialogTitle>{metaMap[mode].title}</DialogTitle>
          <DialogDescription>{metaMap[mode].desc}</DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form
            onSubmit={form.handleSubmit(handleSubmit)}
            className="flex flex-col gap-4"
          >
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Full Name *</FormLabel>
                  <FormControl>
                    <Input placeholder="Enter full name" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="email"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Email Address *</FormLabel>
                  <FormControl>
                    <Input
                      type="email"
                      placeholder="Enter email address"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="role_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Role *</FormLabel>
                  <Select onValueChange={field.onChange} value={field.value}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Select a role" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {roles.map((role) => (
                        <SelectItem key={role.id} value={role.id}>
                          {role.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            <DialogFooter className="mt-2 sm:justify-start">
              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Saving...
                  </>
                ) : (
                  'Save User'
                )}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
};

export default UserFormModal;
