import {
  TRequestCreateRole,
  TRequestUpdateRole
} from '@/api/user-management/type';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { zodResolver } from '@hookform/resolvers/zod';
import { Loader2 } from 'lucide-react';
import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { RoleFormSchema, TRoleFormData } from './schema';

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

  const handleSubmit = (data: TRoleFormData) => {
    onSubmit(data);
  };

  useEffect(() => {
    if (defaultValues) {
      form.reset(defaultValues);
    } else {
      form.reset({
        name: '',
        description: '',
        is_local: true,
        is_portal: false
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
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Description *</FormLabel>
                  <FormControl>
                    <Input placeholder="Enter role description" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="is_local"
              render={({ field }) => (
                <FormItem className="flex flex-row items-center justify-between">
                  <div className="space-y-0.5">
                    <FormLabel className="text-base">Is Local</FormLabel>
                    <p className="text-sm text-muted-foreground">
                      Enable if this is a local role
                    </p>
                  </div>
                  <FormControl>
                    <Switch
                      checked={field.value}
                      onCheckedChange={field.onChange}
                    />
                  </FormControl>
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="is_portal"
              render={({ field }) => (
                <FormItem className="flex flex-row items-center justify-between">
                  <div className="space-y-0.5">
                    <FormLabel className="text-base">Is Portal</FormLabel>
                    <p className="text-sm text-muted-foreground">
                      Enable if this is a portal role
                    </p>
                  </div>
                  <FormControl>
                    <Switch
                      checked={field.value}
                      onCheckedChange={field.onChange}
                    />
                  </FormControl>
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
