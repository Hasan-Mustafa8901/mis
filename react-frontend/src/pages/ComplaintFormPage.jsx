import { Component } from 'react';
import ComplaintsPage from './ComplaintsPage';

class ComplaintErrorBoundary extends Component {
  constructor(props) {
    super(props);

    this.state = {
      hasError: false,
      error: null,
    };
  }

  static getDerivedStateFromError(error) {
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error, info) {
    console.error('Complaint Form crashed:', error);
    console.error('Complaint Form crash details:', info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="m-6 rounded-3xl border border-red-200 bg-red-50 p-6 text-red-800">
          <h1 className="text-xl font-black">Complaint Form Error</h1>

          <p className="mt-2 text-sm font-semibold">
            The complaint form failed to load. Please check the browser console
            for complete error details.
          </p>

          <pre className="mt-4 overflow-auto rounded-2xl bg-white p-4 text-xs text-red-700">
            {String(this.state.error?.message || this.state.error)}
          </pre>
        </div>
      );
    }

    return this.props.children;
  }
}

export default function ComplaintFormPage() {
  return (
    <ComplaintErrorBoundary>
      <ComplaintsPage mode="form" />
    </ComplaintErrorBoundary>
  );
}