export const Loader = () => {
  return (
    <div className="flex flex-col items-center justify-center space-y-4 py-12">
      <p className="animate-pulse text-lg font-semibold tracking-widest text-gray-700">
        LOADING......
      </p>
      <div className="flex space-x-2">
        <div className="h-3 w-3 animate-bounce rounded-full bg-indigo-500"></div>
        <div className="h-3 w-3 animate-bounce rounded-full bg-indigo-500 [animation-delay:-0.2s]"></div>
        <div className="h-3 w-3 animate-bounce rounded-full bg-indigo-500 [animation-delay:-0.4s]"></div>
      </div>
    </div>
  );
};
