import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

const OAuthCallbackPage = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [dots, setDots] = useState('');

  useEffect(() => {
    const interval = setInterval(() => {
      setDots((prev) => (prev.length >= 3 ? '' : prev + '.'));
    }, 400);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const token = searchParams.get('id');
    if (!token) {
      navigate('/auth/signin?error=Login Failed');
    }

    // TODO: validate token
    const timer = setTimeout(() => {
      navigate('/');
    }, 3000);

    return () => clearTimeout(timer);
  }, [navigate, searchParams]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-[#f8f8f9] text-center font-sans transition-opacity duration-500">
      <div className="flex flex-col items-center justify-center">
        <img
          src="/icons/logo.png"
          alt="Combiphar Logo"
          className="h-10 w-auto animate-pulse"
        />
        <h1 className="mt-4 text-xl font-semibold text-gray-700">
          Finalizing Login
        </h1>
        <p className="mt-2 text-lg text-gray-500">
          Please wait while we securely log you in{dots}
        </p>
      </div>
    </div>
  );
};

export default OAuthCallbackPage;
