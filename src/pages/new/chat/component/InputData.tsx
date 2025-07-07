import {
  PlusCircledIcon,
  ImageIcon,
  ArrowRightIcon
} from '@radix-ui/react-icons'; // Assuming you have these icons

const InputData = ({ handleClick, text, setText, setPdfFile }) => {
  //   const [text, setText] = useState("");
  //   const [pdfFile, setPdfFile] = useState(null);

  const handleChange = (e) => {
    setText(e.target.value);
  };

  const handleFileDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      const file = files[0];
      if (file.type === 'application/pdf') {
        setPdfFile(file);
        setText(`File: ${file.name}`); // Optional: update the textarea with file name
      }
    }
  };

  const handleFileInputChange = (e) => {
    const file = e.target.files[0];
    if (file && file.type === 'application/pdf') {
      setPdfFile(file);
      setText(`File: ${file.name}`); // Optional: update the textarea with file name
    }
  };

  return (
    <div
      className="mt-16 w-full rounded-xl border border-gray-300 bg-white p-4"
      onDrop={handleFileDrop}
      onDragOver={(e) => e.preventDefault()} // Prevent default drag behavior
    >
      <textarea
        className="w-full resize-none border-none text-sm outline-none placeholder:text-gray-400"
        rows={4}
        placeholder="Ask CombipharGPT whatever you want....."
        maxLength={1000}
        value={text}
        onChange={handleChange}
      />

      <div className="mt-4 flex items-center justify-between text-sm text-gray-800">
        <div className="flex items-center gap-6">
          <button className="flex items-center gap-1 transition hover:text-purple-600">
            <PlusCircledIcon /> Add attachment
          </button>
          <button className="flex items-center gap-1 transition hover:text-purple-600">
            <ImageIcon /> Use image
          </button>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-900">{text.length}/1000</span>
          <button
            className="flex h-8 w-8 items-center justify-center rounded-md bg-[#7051f8] text-white transition hover:bg-[#5b3de4]"
            onClick={handleClick}
          >
            <ArrowRightIcon />
          </button>
        </div>
      </div>

      {/* File input (hidden) for manual file selection */}
      <input
        type="file"
        accept="application/pdf"
        className="hidden"
        onChange={handleFileInputChange}
      />
    </div>
  );
};

export default InputData;
