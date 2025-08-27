export const ModernLoadingIndicator = () => {
  return (
    <div className="flex w-full justify-start p-4">
      <div className="flex max-w-[100%] gap-3">
        <div className="flex h-10 w-10 flex-shrink-0 animate-pulse items-center justify-center rounded-full bg-gradient-to-r from-purple-500 to-blue-500 shadow-lg">
          <img src="/icons/logo-short.png" className="h-6 w-6" />
        </div>
        <div className="flex items-center gap-2">
          <div className="flex space-x-1">
            <div className="h-2 w-2 animate-bounce rounded-full bg-purple-500"></div>
            <div
              className="h-2 w-2 animate-bounce rounded-full bg-blue-500"
              style={{ animationDelay: '0.1s' }}
            ></div>
            <div
              className="h-2 w-2 animate-bounce rounded-full bg-indigo-500"
              style={{ animationDelay: '0.2s' }}
            ></div>
          </div>
        </div>
      </div>
    </div>
  );
};
