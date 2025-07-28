import { EyeOpenIcon, EyeClosedIcon, UpdateIcon } from '@radix-ui/react-icons';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle
} from '@/components/ui/card';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { useSession } from '@/components/providers/session';
import { LoginSchema, TLoginFormData } from './components/schema';
import { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { SessionToken } from '@/lib/cookies';

export default function LoginPage() {
  const [showPassword, setShowPassword] = useState(false);
  const { signin, status } = useSession();
  const token = SessionToken.get();
  const [error, setError] = useState('');
  const loading = status === 'authenticating';
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const form = useForm<TLoginFormData>({
    mode: 'onChange',
    resolver: zodResolver(LoginSchema)
  });

  const handleSubmit = async (data: TLoginFormData) => {
    setError('');
    try {
      await signin(data);
    } catch (error) {
      const errMsg =
        (error as any)?.response?.data?.message ||
        (error instanceof Error ? error.message : 'Unknown error');
      setError(errMsg);
    }
  };

  const handleSsoLogin = () => {
    window.location.href = `https://portal.combiphar.com`;
  };

  useEffect(() => {
    const error = searchParams.get('error');
    if (error) {
      setError(error);
    }
    return () => setError('');
  }, [searchParams]);

  useEffect(() => {
    if (token) {
      navigate('/');
    }
  }, [token, navigate]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#f8f8f9] font-sans">
      <Card className="mx-auto w-full max-w-md">
        <CardHeader className="space-y-1 text-center">
          <div className="mb-2 flex items-center justify-center">
            <img src="/icons/logo.png" alt="Combiphar Logo" className="w-52" />
          </div>
          <CardTitle className="text-xl">Welcome back</CardTitle>
          <CardDescription>
            Please enter your details to continue.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form
              onSubmit={form.handleSubmit(handleSubmit)}
              className="space-y-4"
            >
              <FormField
                control={form.control}
                name="username"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Username</FormLabel>
                    <FormControl>
                      <Input placeholder="Enter your username" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Password</FormLabel>
                    <FormControl>
                      <div className="relative">
                        <Input
                          type={showPassword ? 'text' : 'password'}
                          placeholder="Enter your password"
                          {...field}
                        />
                        <button
                          type="button"
                          onClick={() => setShowPassword(!showPassword)}
                          className="absolute inset-y-0 right-0 flex items-center px-3 text-gray-400 hover:text-gray-600"
                          aria-label="Toggle password visibility"
                        >
                          {showPassword ? (
                            <EyeClosedIcon className="h-5 w-5" />
                          ) : (
                            <EyeOpenIcon className="h-5 w-5" />
                          )}
                        </button>
                      </div>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              {error && (
                <div className="rounded-md border border-red-300 bg-red-50 p-3 text-center text-sm text-red-600">
                  {error}
                </div>
              )}
              <Button type="submit" disabled={loading} className="w-full">
                {loading ? (
                  <>
                    <UpdateIcon className="mr-2 h-5 w-5 animate-spin" />
                    <span>Logging in...</span>
                  </>
                ) : (
                  <span>Login</span>
                )}
              </Button>
              <div className="relative my-4">
                <div className="absolute inset-0 flex items-center">
                  <span className="w-full border-t"></span>
                </div>
                <div className="relative flex justify-center text-xs uppercase">
                  <span className="bg-background px-2 text-muted-foreground">
                    Or continue with
                  </span>
                </div>
              </div>
              <Button
                variant="outline"
                type="button"
                className="w-full"
                onClick={handleSsoLogin}
              >
                Login with SSO
              </Button>
              <div className="mt-2 text-center">
                <Link
                  className=" text-xs"
                  to="https://portal.combiphar.com/Apps/open/combiai"
                >
                  Direct to SSO (for testing only)
                </Link>
              </div>
            </form>
          </Form>
        </CardContent>
        <CardFooter>
          <p className="text-center text-sm text-gray-500">
            © {new Date().getFullYear()} Combiphar. All rights reserved.
          </p>
        </CardFooter>
      </Card>
    </div>
  );
}
