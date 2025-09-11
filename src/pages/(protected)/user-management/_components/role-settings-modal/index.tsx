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
import { Input } from '@/components/ui/input';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '@/components/ui/table';
import { Loader2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import useGetSettings from '../../_hooks/get-settings';

interface Props {
  open?: boolean;
  onOpenChange: () => void;
  roleData: TRole | null;
  onSave: (
    settings: { role_id: number; setting_id: string; value: string }[]
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
  const [settingsValues, setSettingsValues] = useState<Record<string, string>>(
    {}
  );
  const settingsQuery = useGetSettings();
  const settings = settingsQuery.data?.data || [];

  useEffect(() => {
    if (open && settings.length > 0) {
      // Initialize settings values with defaults
      const initialValues: Record<string, string> = {};
      settings.forEach((setting) => {
        initialValues[setting.name] = setting.input;
      });
      setSettingsValues(initialValues);
    }
  }, [open, settings]);

  const handleValueChange = (name: string, value: string) => {
    setSettingsValues((prev) => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSave = () => {
    if (!roleData?.id) return;

    const settingsArray = settings
      .filter((setting) => settingsValues[setting.name] !== undefined)
      .map((setting) => ({
        role_id: roleData.id!,
        setting_id: setting.id,
        value: settingsValues[setting.name] || setting.input
      }));
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
                  <TableRow key={setting.id}>
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
                      <Input
                        value={settingsValues[setting.name] || ''}
                        onChange={(e) =>
                          handleValueChange(setting.name, e.target.value)
                        }
                        placeholder="Enter value"
                        className="w-full"
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
            type="button"
            onClick={handleSave}
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
      </DialogContent>
    </Dialog>
  );
};

export default RoleSettingsModal;
