import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog';
import { useForm } from 'react-hook-form';
import { RoleFormSchema, TRoleFormData } from './schema';
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
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { useEffect } from 'react';
import {
  TRequestCreateRole,
  TRequestUpdateRole
} from '@/api/user-management/type';
import { Loader2 } from 'lucide-react';
import useGetPermissions from '../../_hooks/get-permissions';

interface Props {
  loading?: boolean;
  open?: boolean;
  onOpenChange: () => void;
  mode: 'create' | 'edit';
  defaultValues?: Partial<TRoleFormData>;
  onSubmit: (data: TRequestCreateRole | TRequestUpdateRole) => void;
}

const RoleFormModal = ({
  defaultValues,
  open,
  onOpenChange,
  onSubmit,
  mode,
  loading
}: Props) => {
  const metaMap: Record<Props['mode'], { title: string; desc: string }> = {
    create: {
      title: 'Add New Role',
      desc: 'Create a new role with specific permissions.'
    },
    edit: {
      title: 'Edit Role',
      desc: 'Update role name and permissions.'
    }
  };

  const form = useForm<TRoleFormData>({
    mode: 'onChange',
    resolver: zodResolver(RoleFormSchema)
  });

  const permissionsQuery = useGetPermissions();
  const permissions = permissionsQuery.data?.data || [];

  const handleSubmit = (data: TRoleFormData) => {
    onSubmit(data);
  };

  useEffect(() => {
    if (defaultValues) {
      form.reset(defaultValues);
    } else {
      form.reset({
        name: '',
        permission_ids: []
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
                  <FormLabel>Role Name *</FormLabel>
                  <FormControl>
                    <Input placeholder="Enter role name" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="permission_ids"
              render={() => (
                <FormItem>
                  <div className="mb-4">
                    <FormLabel className="text-base">Permissions *</FormLabel>
                    <p className="text-sm text-muted-foreground">
                      Select the permissions this role should have
                    </p>
                  </div>
                  <div className="space-y-3">
                    {permissions.map((permission) => (
                      <FormField
                        key={permission.id}
                        control={form.control}
                        name="permission_ids"
                        render={({ field }) => {
                          return (
                            <FormItem
                              key={permission.id}
                              className="flex flex-row items-start space-x-3 space-y-0"
                            >
                              <FormControl>
                                <Checkbox
                                  checked={field.value?.includes(permission.id)}
                                  onCheckedChange={(checked) => {
                                    return checked
                                      ? field.onChange([
                                          ...field.value,
                                          permission.id
                                        ])
                                      : field.onChange(
                                          field.value?.filter(
                                            (value) => value !== permission.id
                                          )
                                        );
                                  }}
                                />
                              </FormControl>
                              <div className="space-y-1 leading-none">
                                <FormLabel className="font-normal">
                                  {permission.name}
                                </FormLabel>
                              </div>
                            </FormItem>
                          );
                        }}
                      />
                    ))}
                  </div>
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
                  'Save Role'
                )}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
};

export default RoleFormModal;
