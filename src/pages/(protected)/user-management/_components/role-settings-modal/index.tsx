import { TRole } from '@/api/user-management/type';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog';
import { Form, FormControl, FormField, FormItem } from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '@/components/ui/table';
import { zodResolver } from '@hookform/resolvers/zod';
import { Loader2 } from 'lucide-react';
import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import useGetRoleSettings from '../../_hooks/get-role-settings';
import { RoleSettingsSchema, TRoleSettingsFormData } from './schema';

interface Props {
  open?: boolean;
  onOpenChange: () => void;
  roleData: TRole | null;
  onSave: (
    settings: { role_id: string; setting_id: string; value: unknown }[]
  ) => void;
  loading?: boolean;
}

const RoleSettingsModal = ({
  open,
  onOpenChange,
  roleData,
  onSave,
  loading
}: Props) => {
  const settingsQuery = useGetRoleSettings(roleData?.id?.toString() || '');
  const settings = settingsQuery.data?.data || [];

  const form = useForm<TRoleSettingsFormData>({
    resolver: zodResolver(RoleSettingsSchema),
    defaultValues: {}
  });

  // Reset form when modal closes and refetch when opens
  useEffect(() => {
    if (open) {
      // Refetch data when modal opens to get latest values
      settingsQuery.refetch();
    } else {
      form.reset({});
    }
  }, [open]);

  // Populate form when data is loaded and modal is open
  useEffect(() => {
    if (
      open &&
      settingsQuery.data?.data &&
      settingsQuery.data.data.length > 0
    ) {
      const initialValues: TRoleSettingsFormData = {};
      settingsQuery.data.data.forEach((setting) => {
        initialValues[setting.name] = setting.value;
      });
      form.reset(initialValues);
    }
  }, [open, settingsQuery.data, settingsQuery.dataUpdatedAt]);

  const handleSubmit = (formData: TRoleSettingsFormData) => {
    if (!roleData?.id) return;

    const settingsArray = settings.map((setting) => {
      const formValue = formData[setting.name];
      let value: string | boolean | number;

      if (formValue !== undefined && formValue !== null) {
        if (setting.data_type === 'boolean') {
          value = formValue;
        } else if (setting.data_type === 'integer') {
          value = parseInt(formValue.toString());
        } else {
          value = formValue;
        }
      } else {
        value = setting.value.toString();
      }

      return {
        role_id: setting.role_id,
        setting_id: setting.setting_id,
        value
      };
    });

    onSave(settingsArray);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="no-scrollbar sm:max-w-lg"
        onInteractOutside={(e) => e.preventDefault()}
        onOpenAutoFocus={(e) => e.preventDefault()}
      >
        <DialogHeader>
          <DialogTitle>Role Settings</DialogTitle>
          <DialogDescription>
            Configure settings for role: {roleData?.name}
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form
            id="role-settings-form"
            onSubmit={form.handleSubmit(handleSubmit)}
            className="space-y-4"
          >
            <div className="max-h-96 overflow-y-auto">
              {settingsQuery.isLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin" />
                  <span className="ml-2">Loading settings...</span>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-16">No</TableHead>
                      <TableHead>Name</TableHead>
                      <TableHead>Value</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {settings.map((setting, index) => (
                      <TableRow key={setting.setting_id}>
                        <TableCell>{index + 1}</TableCell>
                        <TableCell>
                          <div>
                            <div className="font-medium">{setting.name}</div>
                            <div className="text-sm text-muted-foreground">
                              {setting.description}
                            </div>
                          </div>
                        </TableCell>
                        <TableCell>
                          <FormField
                            control={form.control}
                            name={setting.name}
                            render={({ field }) => (
                              <FormItem>
                                <FormControl>
                                  {setting.data_type === 'boolean' ? (
                                    <div className="flex items-center space-x-2">
                                      <Switch
                                        checked={!!field.value}
                                        onCheckedChange={field.onChange}
                                      />
                                    </div>
                                  ) : (
                                    <Input
                                      type="number"
                                      value={field.value?.toString() || ''}
                                      onChange={(e) =>
                                        field.onChange(e.target.value)
                                      }
                                      placeholder="Enter value"
                                      className="w-full"
                                    />
                                  )}
                                </FormControl>
                              </FormItem>
                            )}
                          />
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </div>

            <DialogFooter className="mt-4">
              <Button
                type="button"
                variant="outline"
                onClick={onOpenChange}
                disabled={loading}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={loading || settingsQuery.isLoading}
              >
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Saving...
                  </>
                ) : (
                  'Save Settings'
                )}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
};

export default RoleSettingsModal;
