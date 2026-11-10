import React, { useState } from 'react';
import CodeEditor from '../components/CodeEditor';
import Button from '../components/Button';

const AssessmentPage = () => {
  const [code, setCode] = useState('#include <stdio.h>\n\nint main() {\n    // Write your code here\n    return 0;\n}');

  return (
    <div className="flex h-full p-4 gap-4">
      {/* Question Section */}
      <div className="w-1/3 bg-white dark:bg-gray-800 p-6 rounded-lg shadow overflow-y-auto">
        <h1 className="text-2xl font-bold mb-4">Sum of Numbers</h1>
        <p className="text-gray-600 dark:text-gray-300 mb-6">
          Write a C program to calculate the sum of two integers.
        </p>
        <div className="bg-gray-100 dark:bg-gray-700 p-4 rounded mb-4">
          <h3 className="font-semibold mb-2">Input Format:</h3>
          <p>Two integers on a single line.</p>
        </div>
      </div>

      {/* Editor Section */}
      <div className="flex-1 flex flex-col gap-4">
        <div className="flex-1 min-h-0">
          <CodeEditor code={code} onChange={setCode} />
        </div>
        <div className="flex justify-end gap-2">
          <Button variant="secondary">Run Sample</Button>
          <Button variant="primary">Submit Code</Button>
        </div>
      </div>
    </div>
  );
};

export default AssessmentPage;
