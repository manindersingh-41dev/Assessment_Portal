import React, { useRef, useState } from 'react';
import Editor, { loader } from '@monaco-editor/react';
import { useThemeStore } from '../store/themeStore';

loader.config({
  paths: { vs: `${import.meta.env.BASE_URL}vendor/monaco/vs` },
});

const CodeEditor = ({
  code,
  onChange,
  language = 'c',
  readOnly = false,
  fontSize = 14,
  ariaLabel = 'Code editor',
  className = '',
}) => {
  const theme = useThemeStore((state) => state.theme);
  const isDarkMode = theme === 'dark';
  const [editorReady, setEditorReady] = useState(false);
  const keydownMetadataRef = useRef(null);

  const captureKeydown = (event) => {
    const keyboardEvent = event.nativeEvent || event;
    keydownMetadataRef.current = {
      repeat: Boolean(keyboardEvent.repeat),
      key: keyboardEvent.key,
      isPrintable: typeof keyboardEvent.key === 'string'
        && keyboardEvent.key.length === 1
        && !keyboardEvent.ctrlKey
        && !keyboardEvent.metaKey
        && !keyboardEvent.altKey
        && !keyboardEvent.isComposing,
      at: performance.now(),
    };
  };

  const consumeInputMetadata = () => {
    const metadata = keydownMetadataRef.current;
    keydownMetadataRef.current = null;
    if (!metadata || performance.now() - metadata.at > 100) return null;
    return metadata;
  };

  const handleEditorChange = (value) => {
    onChange?.(value ?? '', consumeInputMetadata());
  };

  return (
    <div
      className={`relative h-full w-full overflow-hidden rounded-md border border-gray-200 dark:border-gray-700 ${className}`}
      onKeyDownCapture={captureKeydown}
    >
      {!editorReady && (
        <textarea
          aria-label={`${ariaLabel} loading`}
          autoCapitalize="off"
          autoComplete="off"
          autoCorrect="off"
          className="absolute inset-0 z-10 h-full w-full resize-none bg-slate-950 p-4 font-mono text-sm leading-6 text-slate-100 outline-none focus:ring-2 focus:ring-primary-500"
          onChange={(event) => onChange?.(event.target.value, consumeInputMetadata())}
          readOnly={readOnly}
          spellCheck={false}
          value={code}
        />
      )}
      <Editor
        height="100%"
        language={language}
        value={code}
        theme={isDarkMode ? 'vs-dark' : 'light'}
        onChange={handleEditorChange}
        onMount={() => setEditorReady(true)}
        options={{
          readOnly,
          ariaLabel,
          contextmenu: false,
          fontSize,
          minimap: { enabled: false },
          scrollBeyondLastLine: false,
          automaticLayout: true,
          padding: { top: 10, bottom: 10 },
          lineNumbers: 'on',
          renderLineHighlight: 'all',
          cursorStyle: 'line',
          wordWrap: 'on',
        }}
      />
    </div>
  );
};

export default CodeEditor;
